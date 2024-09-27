# Debian 11 is recommended.
FROM debian:11-slim

# Suppress interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# (Required) Install utilities required by Spark scripts.
RUN apt update && apt install -y procps tini libjemalloc2

# (Optiona) Install utilities required by XGBoost for Spark.
RUN apt install -y procps libgomp1

# Enable jemalloc2 as default memory allocator
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# (Optional) Add extra jars.
ENV SPARK_EXTRA_JARS_DIR=/opt/spark/jars/
ENV SPARK_EXTRA_CLASSPATH='/opt/spark/jars/*'
RUN mkdir -p "${SPARK_EXTRA_JARS_DIR}"
RUN (cd "${SPARK_EXTRA_JARS_DIR}" && curl -O "https://storage.googleapis.com/spark-lib/bigquery/spark-3.5-bigquery-0.41.0.jar")

# (Optional) Install and configure Miniforge3.
ENV MAMBA_HOME=/opt/miniforge3
ENV PYSPARK_PYTHON=${MAMBA_HOME}/bin/python
ENV PATH=${MAMBA_HOME}/bin:${PATH}
RUN curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
RUN bash Miniforge3-Linux-x86_64.sh -b -p ${MAMBA_HOME}

# (Optional) Install Conda packages using Mamba.
#
# The following packages are installed in the default image, it is strongly
# recommended to include all of them.
#
# Use mamba to install packages quickly.
RUN ${MAMBA_HOME}/bin/mamba install \
      cython \
      fastavro \
      fastparquet \
      fasttext \
      gcsfs \
      google-cloud-aiplatform \
      google-cloud-bigquery-storage \
      google-cloud-bigquery[pandas] \
      google-cloud-bigtable \
      google-cloud-container \
      google-cloud-datacatalog \
      google-cloud-dataproc \
      google-cloud-datastore \
      google-cloud-language \
      google-cloud-logging \
      google-cloud-monitoring \
      google-cloud-pubsub \
      google-cloud-redis \
      google-cloud-spanner \
      google-cloud-speech \
      google-cloud-storage \
      google-cloud-texttospeech \
      google-cloud-translate \
      google-cloud-vision \
      ipykernel \
      ipython \
      koalas \
      matplotlib \
      nltk \
      numba \
      numpy \
      openblas \
      optimum \
      orc \
      pandas \
      pyarrow \
      pysal \
      pytables \
      python \
      regex \
      requests \
      rtree \
      scikit-image \
      scikit-learn \
      scipy \
      seaborn \
      sentence_transformers \
      sqlalchemy \
      sympy \
      tiktoken \
      tldextract \
      transformers \
      virtualenv \
      zstandard
      
# (Required) Create the 'spark' group/user.
# The GID and UID must be 1099. Home directory is required.
RUN groupadd -g 1099 spark
RUN useradd -u 1099 -g 1099 -d /home/spark -m spark
USER spark