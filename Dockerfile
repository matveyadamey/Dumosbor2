FROM python:3.11-slim

WORKDIR /app


ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1  

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core
COPY api ./api
COPY bot ./bot
COPY runner.py ./
COPY alembic.ini ./
COPY alembic ./alembic

CMD ["python", "runner.py"]