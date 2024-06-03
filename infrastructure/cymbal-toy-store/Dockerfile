FROM node:18

COPY frontend /opt/frontend
WORKDIR /opt/frontend

RUN npm install
RUN npm run build


FROM python:3.11

ENV GOOGLE_CLOUD_PROJECT=dbs-next-demo-01

COPY --from=0 /opt/frontend/out /opt/frontend/out
COPY backend /opt/backend
WORKDIR /opt/backend
RUN pip install poetry==1.4.0
RUN poetry install
RUN mv /opt/backend/src/backend/.env-prod /opt/backend/src/backend/.env
ENV POETRY_CACHE_DIR="/root/.cache/pypoetry"
#COPY credentials.json /opt/credentials.json

CMD ["poetry", "run", "python", "src/backend/app.py"]
#CMD ["poetry", "config", "--list"]