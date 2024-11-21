# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
RUN pip install poetry
RUN poetry install
RUN mv /opt/backend/src/backend/.env-prod /opt/backend/src/backend/.env
ENV POETRY_CACHE_DIR="/root/.cache/pypoetry"
#COPY credentials.json /opt/credentials.json

CMD ["poetry", "run", "python", "src/backend/app.py"]
