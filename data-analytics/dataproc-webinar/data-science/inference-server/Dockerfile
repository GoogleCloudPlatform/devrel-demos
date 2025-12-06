FROM python:3.12-slim

# Install OpenJDK-21 (Required for Spark)
RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless procps curl && \
    rm -rf /var/lib/apt/lists/*

# Setup Spark GCS Connector
ENV SPARK_HOME=/usr/local/lib/python3.12/site-packages/pyspark
ENV SPARK_CONF_DIR=${SPARK_HOME}/conf

# Create Spark conf directory and download GCS connector
RUN mkdir -p ${SPARK_HOME}/jars && \
    curl -o ${SPARK_HOME}/jars/gcs-connector-hadoop3-latest.jar https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop3-latest.jar && \
    mkdir -p ${SPARK_CONF_DIR} && \
    echo "spark.hadoop.fs.gs.impl=com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem" >> ${SPARK_CONF_DIR}/spark-defaults.conf && \
    echo "spark.hadoop.fs.AbstractFileSystem.gs.impl=com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS" >> ${SPARK_CONF_DIR}/spark-defaults.conf && \
    echo "spark.hadoop.google.cloud.auth.service.account.enable=true" >> ${SPARK_CONF_DIR}/spark-defaults.conf

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
