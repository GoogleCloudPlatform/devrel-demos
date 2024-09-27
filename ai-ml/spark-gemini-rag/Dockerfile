FROM python:3.11

RUN mkdir /home/app
WORKDIR /home

COPY requirements.txt /home/app/requirements.txt
COPY main.py /home/app/main.py

RUN python3 -m pip install -r /home/app/requirements.txt

# Preload the model into the image
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-miniLM-L6-v2')"

CMD ["python3", "/home/app/main.py"]