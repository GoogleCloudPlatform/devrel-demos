FROM python:3.11-slim

WORKDIR /usr/src/app

ARG GRADIO_SERVER_PORT=8080

COPY requirements.txt ./

COPY gradio_app.py ./

RUN pip3 install -r requirements.txt

# Dirty fix for https://github.com/gradio-app/gradio/pull/7707 regression
RUN sed -i 's/except (ConnectionError, httpx.ConnectError)/except (ConnectionError, httpx.ConnectError, httpx.TimeoutException)/g' /usr/local/lib/python3.11/site-packages/gradio/networking.py

COPY . .

CMD ["python3", "./gradio_app.py"]
