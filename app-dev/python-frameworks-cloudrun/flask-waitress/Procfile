FROM python:slim

ENV APP_HOME /app
ENV PORT 8080
ENV PYTHONUNBUFFERED 1
EXPOSE $PORT
WORKDIR $APP_HOME

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD exec waitress-serve --port $PORT app:app 
