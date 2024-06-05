FROM node:18

COPY frontend /opt/frontend
WORKDIR /opt/frontend

RUN npm install
RUN npm run build


FROM python:3.11

# Put your project here
ENV GOOGLE_CLOUD_PROJECT=cymbal-demo

COPY --from=0 /opt/frontend/out /opt/frontend/out
COPY backend /opt/backend
WORKDIR /opt/backend
RUN pip install poetry==1.4.0
RUN poetry install
RUN mv /opt/backend/src/backend/.env-prod /opt/backend/src/backend/.env
ENV POETRY_CACHE_DIR="/root/.cache/pypoetry"
#COPY credentials.json /opt/credentials.json

CMD ["poetry", "run", "python", "src/backend/app.py"]
