FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# main.py를 실행하여 유비콘(Uvicorn) 구동
CMD ["python", "main.py"]
