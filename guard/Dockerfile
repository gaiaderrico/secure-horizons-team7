# MIRAGE guard. Build context = repo root (it needs mirage/contracts.py and mirage/fakes.py).
FROM python:3.12-slim
WORKDIR /app
COPY mirage/contracts.py mirage/fakes.py /app/mirage/
COPY guard/guard.py /app/guard.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "guard.py", "run"]
