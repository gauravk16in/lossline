import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
import httpx
import websockets
from simulator.lossline_simulator.predictive_runner import run_predictive_demo

from simulator.lossline_simulator.scenarios.lunch_rush import generate_scenario_events

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("simulator")


async def post_event(client: httpx.AsyncClient, api_url: str, event: dict) -> bool:
    """
    POSTs a single event envelope to the backend events ingestion API.
    """
    url = f"{api_url}/api/v1/events"
    try:
        response = await client.post(url, json=event, timeout=30.0)
        if response.status_code in [200, 202]:
            data = response.json()
            logger.debug(
                f"Event {event['event_id']} accepted. Duplicate: {data.get('duplicate')}"
            )
            return True
        else:
            logger.error(
                f"Failed to post event {event['event_id']}: Code {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Network error posting event {event['event_id']}: {e}")
        return False


async def wait_for_manager_approval(api_url: str) -> None:
    """
    Blocks until the manager approves the recommended action.
    Listens to WebSockets for status change notifications, falling back to polling.
    """
    logger.info(
        "Simulation paused at degradation phase. Waiting for manager approval..."
    )

    ws_url = (
        api_url.replace("http://", "ws://").replace("https://", "wss://") + "/api/v1/ws"
    )
    approval_event = asyncio.Event()

    # Task to listen on Websocket
    async def listen_ws():
        try:
            async with websockets.connect(ws_url) as ws:
                logger.info("Connected to WebSocket transition feed.")
                while True:
                    msg_str = await ws.recv()
                    msg = json.loads(msg_str)
                    logger.info(f"WebSocket notification: {msg}")
                    # In endpoints.py: stage is set to incident.status which transitions to ACTION_APPROVED
                    if msg.get("stage") == "ACTION_APPROVED":
                        logger.info("Manager approval detected via WebSocket!")
                        approval_event.set()
                        return
        except Exception as e:
            logger.warning(
                f"WebSocket connection failed or disconnected: {e}. Falling back to polling."
            )
            # Do not set event, let polling task run

    # Task to poll REST endpoint
    async def poll_rest():
        poll_url = f"{api_url}/api/v1/incidents"
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(poll_url, timeout=5.0)
                    if response.status_code == 200:
                        incidents = response.json()
                        for inc in incidents:
                            # If any incident has moved to ACTION_APPROVED
                            if inc.get("status") == "ACTION_APPROVED":
                                logger.info(
                                    "Manager approval detected via REST polling!"
                                )
                                approval_event.set()
                                return
                except Exception as e:
                    logger.warning(f"Polling check failed: {e}")
                await asyncio.sleep(2.0)

    ws_task = asyncio.create_task(listen_ws())
    poll_task = asyncio.create_task(poll_rest())

    # Wait until the approval event is set
    await approval_event.wait()

    # Cancel pending tasks
    ws_task.cancel()
    poll_task.cancel()

    logger.info("Resuming simulation pipeline...")


async def run_simulation(api_url: str, speed: float, seed: int):
    """
    Generates and plays the Meghana Biryani lunch-rush scenario sequence.
    """
    start_time = datetime.now(timezone.utc)

    # 1. Generate events
    logger.info("Generating scenario events...")
    baseline_events, pre_approval_events, post_approval_events = (
        generate_scenario_events(start_time=start_time, seed=seed)
    )

    async with httpx.AsyncClient() as client:
        # 2. Reset database for clean run
        logger.info("Resetting demo database...")
        try:
            reset_resp = await client.post(f"{api_url}/api/v1/demo/reset", timeout=15.0)
            if reset_resp.status_code != 200:
                logger.error(
                    f"Reset database failed: Code {reset_resp.status_code} - {reset_resp.text}"
                )
                sys.exit(1)
            logger.info("Database reset completed successfully.")
        except Exception as e:
            logger.critical(f"Failed to contact reset database endpoint: {e}")
            sys.exit(1)

        run_response = await client.post(
            f"{api_url}/api/v1/demo/runs",
            json={"scenario_id": "meghana_lunch_rush_v1", "seed": seed, "speed": speed},
        )
        run_response.raise_for_status()
        run_id = run_response.json()["id"]

        # 3. Bulk load baseline history
        logger.info(
            f"Fast-posting {len(baseline_events)} historical baseline events in parallel..."
        )

        success = False
        if baseline_events:
            logger.info("Warm-up: posting first event to provision the restaurant...")
            success = await post_event(client, api_url, baseline_events[0])
            if not success:
                logger.error("Warm-up event failed. Proceeding anyway...")

        remaining_events = baseline_events[1:]
        sem = asyncio.Semaphore(10)

        async def post_with_sem(ev):
            async with sem:
                return await post_event(client, api_url, ev)

        results = await asyncio.gather(*(post_with_sem(ev) for ev in remaining_events))
        success_count = sum(1 for r in results if r) + (1 if success else 0)
        logger.info(
            f"Baseline loaded successfully ({success_count}/{len(baseline_events)} events ingested)."
        )

        # 4. Stream pre-approval live events (Healthy -> Surge -> Degradation)
        logger.info(
            f"Streaming {len(pre_approval_events)} live events with speed multiplier {speed}..."
        )
        first_event_time = datetime.fromisoformat(pre_approval_events[0]["occurred_at"])

        async def schedule_post(ev, delay_sec):
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)
            await post_event(client, api_url, ev)

        tasks = []
        for ev in pre_approval_events:
            ev_time = datetime.fromisoformat(ev["occurred_at"])
            offset_seconds = (ev_time - first_event_time).total_seconds()
            delay = offset_seconds / speed
            tasks.append(asyncio.create_task(schedule_post(ev, delay)))

        await asyncio.gather(*tasks)
        logger.info("Live pre-approval events stream completed.")

        # 5. Pause and wait for manager approval
        await wait_for_manager_approval(api_url)

        # 6. Stream post-approval recovery events
        logger.info(f"Streaming {len(post_approval_events)} recovery events...")
        first_rec_time = datetime.fromisoformat(post_approval_events[0]["occurred_at"])

        rec_tasks = []
        for ev in post_approval_events:
            ev_time = datetime.fromisoformat(ev["occurred_at"])
            offset_seconds = (ev_time - first_rec_time).total_seconds()
            delay = offset_seconds / speed
            rec_tasks.append(asyncio.create_task(schedule_post(ev, delay)))

        await asyncio.gather(*rec_tasks)
        incidents_response = await client.get(f"{api_url}/api/v1/incidents")
        incidents_response.raise_for_status()
        approved = [
            incident
            for incident in incidents_response.json()
            if incident.get("status") == "ACTION_APPROVED"
        ]
        if not approved:
            raise RuntimeError("Approved incident disappeared before verification")
        verify_response = await client.post(
            f"{api_url}/api/v1/incidents/{approved[0]['id']}/verify"
        )
        verify_response.raise_for_status()
        logger.info("Outcome verification: %s", verify_response.json().get("status"))
        complete_response = await client.post(
            f"{api_url}/api/v1/demo/runs/{run_id}/complete"
        )
        complete_response.raise_for_status()
        logger.info("Simulation run completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="LOSSLine operational scenario simulator."
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend FastAPI base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=60.0,
        help="Event time acceleration multiplier. e.g. 60 means 1 minute event-time = 1 second wall-clock (default: 60.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatable synthetic data generation (default: 42)",
    )
    parser.add_argument("--scenario", choices=("reactive", "predictive"), default="reactive",
        help="Run the reactive lunch rush or predictive seeded demo.")
    parser.add_argument("--target-window-start", default="2026-09-09T13:00:00+00:00",
        help="Predictive target window start as an aware ISO timestamp.")

    args = parser.parse_args()

    try:
        if args.scenario == "predictive":
            async def predictive_main():
                api_url = args.api_url.rstrip("/")
                async with httpx.AsyncClient(timeout=30) as client:
                    reset = await client.post(f"{api_url}/api/v1/demo/reset"); reset.raise_for_status()
                    evidence = await run_predictive_demo(api_url=api_url, seed=args.seed,
                        target_window_start=datetime.fromisoformat(args.target_window_start), client=client)
                    logger.info("Predictive demo completed: %s", json.dumps({
                        "forecast_count": len(evidence["cycle"]["forecast_ids"]),
                        "outcome_count": len(evidence["outcome_ids"]),
                        "evaluation_count": len(evidence["evaluations"]),
                        "decision_status": evidence["review"]["status"]}, sort_keys=True))
            asyncio.run(predictive_main())
        else:
            asyncio.run(run_simulation(api_url=args.api_url.rstrip("/"), speed=args.speed, seed=args.seed))
    except KeyboardInterrupt:
        logger.info("Simulation aborted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
