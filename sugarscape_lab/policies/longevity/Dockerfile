FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install "websockets==16.1.1"
COPY policy.py .

USER 65532:65532
CMD ["python", "policy.py"]
