# Use a base image with Python 3.10
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Set the PYTHONPATH environment variable
ENV PYTHONPATH=/app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the service port
EXPOSE 5003

# Define the command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5003"]
