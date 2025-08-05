FROM python:3.8-slim

WORKDIR /app
COPY webhook_processor.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "webhook_processor.py"]