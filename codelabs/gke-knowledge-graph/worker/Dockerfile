FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the worker scripts and modules
COPY worker.py process_file.py /app/
COPY processor /app/processor/

# Set runtime default
ENTRYPOINT ["python", "worker.py"]
