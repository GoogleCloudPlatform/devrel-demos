FROM python:3.12-slim

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 -ms /bin/bash appuser

# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir --upgrade \
    pip \
    virtualenv

WORKDIR /home/appuser

COPY . .

ENV VIRTUAL_ENV=/home/appuser/venv
RUN virtualenv ${VIRTUAL_ENV}
RUN . ${VIRTUAL_ENV}/bin/activate && pip install --no-cache-dir -r ./requirements.txt

RUN mkdir -p /home/appuser/.streamlit
COPY .streamlit/config.toml /home/appuser/.streamlit/config.toml

COPY run.sh /home/appuser
RUN chmod +x /home/appuser/run.sh

USER appuser

EXPOSE 8501

ENTRYPOINT ["./run.sh"]