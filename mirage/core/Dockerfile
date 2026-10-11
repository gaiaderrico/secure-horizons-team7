# MIRAGE core API. Build from the repo root:
#   docker build -f mirage/core/Dockerfile -t mirage-core .
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.110" "uvicorn>=0.29" "requests>=2.31" "python-multipart>=0.0.9"
COPY mirage/ /app/mirage/

ENV MIRAGE_DB=/data/core.db \
    PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 80

CMD ["uvicorn", "mirage.core.api:app", "--host", "0.0.0.0", "--port", "80"]
