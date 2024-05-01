FROM python:3.7


# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./


# Install production dependencies.
RUN curl -L \
https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz \
-o go-container registry.tar.gz
RUN tar -zxvf go-containerregistry.tar.gz
RUN chmod +x gcrane
RUN mv gcrane /usr/local/bin/
RUN pip install Flask gunicorn
CMD exec gunicorn --bind :$PORT --workers 3 --threads 3 --log-level debug --timeout 600 app:app
