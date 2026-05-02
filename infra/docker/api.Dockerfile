FROM python:3.12-slim

WORKDIR /app

COPY services /app/services
COPY data /app/data
COPY packages /app/packages

WORKDIR /app/services/api

RUN pip install --no-cache-dir -e .

WORKDIR /app

CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
