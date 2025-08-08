# Use official Python runtime as a base image
FROM python:3.10

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Start Django server listening on all interfaces
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
