# Use an official lightweight Python image as the base
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Create a non-root user for security best practices
RUN adduser --disabled-password --gecos "" myuser

# Copy and install dependencies first to leverage Docker's layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code into the container
COPY . .

# Create the directory where the agent will write files at runtime
# The -p flag ensures the command doesn't fail if the directory already exists
RUN mkdir -p movie_pitches

# Change ownership of EVERYTHING in /app to the non-root user
# Without this, the running agent would be denied permission to write files.
RUN chown -R myuser:myuser /app

# Switch the active user from root to the non-root user
USER myuser

# Add the user's local binary directory to the system's PATH
ENV PATH="/home/myuser/.local/bin:$PATH"

# Define the command to run when the container starts
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]