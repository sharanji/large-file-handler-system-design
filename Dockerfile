# Use an official Python runtime as a base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Copy files into container
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn

COPY . .

# Expose Flask’s default port
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app