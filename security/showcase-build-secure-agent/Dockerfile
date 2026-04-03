# Customize base image
ARG BASE_IMAGE_URL

FROM ${BASE_IMAGE_URL}

# Customize default Python Package Index or use default
ARG PIP_INDEX_URL="https://pypi.org/simple/"

# Set base URL for the Python Package Index
ENV PIP_INDEX_URL=$PIP_INDEX_URL
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Create the user and a home directory
RUN useradd -m -u 1001 myuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only code of the demo keeping folder hierarchy
COPY main.py /app/
COPY customer_service_agent/ /app/customer_service_agent/

RUN chown -R myuser:myuser /app

# DO NOT run under 'root'
USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]