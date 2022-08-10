FROM python:3.7-slim

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

ENV FUNCTION_TARGET function

RUN pip install functions-framework

CMD exec functions-framework
