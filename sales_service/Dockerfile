 # Use a base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the service code to the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port this service will run on (e.g., 5001)
EXPOSE 5004

# Command to run the service
CMD ["python", "app.py"]
