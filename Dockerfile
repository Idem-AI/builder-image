FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir boto3 docker

WORKDIR /app
COPY worker.py /app/worker.py
RUN chmod +x /app/worker.py

ENTRYPOINT ["/app/worker.py"]
