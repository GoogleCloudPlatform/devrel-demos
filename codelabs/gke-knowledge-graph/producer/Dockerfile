FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the producer script
COPY producer.py /app/

# Set runtime default
ENTRYPOINT ["python", "producer.py"]
