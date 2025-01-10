# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy only requirements to cache dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

RUN apt-get update && apt-get install -y curl

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]

