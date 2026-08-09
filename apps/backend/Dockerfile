FROM python:3.12.11-slim
WORKDIR /workspace
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/workspace/apps/backend
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY packages/intelligence /workspace/packages/intelligence
COPY apps/backend/requirements.txt /workspace/apps/backend/requirements.txt
RUN pip install --no-cache-dir -e /workspace/packages/intelligence && pip install --no-cache-dir -r /workspace/apps/backend/requirements.txt
COPY apps/backend /workspace/apps/backend
WORKDIR /workspace/apps/backend
CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
