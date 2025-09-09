# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install Docker CLI to allow the container to stream its own logs
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg tzdata && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We add --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variables
# The Selenium Hub URL can be set during 'docker run'
# Example: docker run -e SELENIUM_HUB_URL="http://my-hub:4444" ...
ENV SELENIUM_HUB_URL="http://host.docker.internal:4444"
ENV TZ=Asia/Seoul

# Make the start script executable
RUN chmod +x /app/start.sh

# Run start.sh when the container launches
CMD ["/app/start.sh"]

