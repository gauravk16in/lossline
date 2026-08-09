FROM python:3.12.11-slim
WORKDIR /workspace
COPY simulator /workspace/simulator
RUN pip install --no-cache-dir httpx==0.28.1 websockets==17.0.1
ENV PYTHONPATH=/workspace
ENTRYPOINT ["python", "-m", "simulator.lossline_simulator.runner"]
CMD ["--api-url", "http://backend:8000", "--speed", "120"]
