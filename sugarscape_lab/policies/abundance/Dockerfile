FROM python:3.12-slim

RUN pip install --no-cache-dir websockets==16.1.1

WORKDIR /app
COPY player.py .

USER 65532:65532
CMD ["python", "/app/player.py"]
