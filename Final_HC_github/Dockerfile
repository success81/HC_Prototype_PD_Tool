# Use an official lightweight Python runtime
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the default port Cloud Run expects
ENV PORT=8080

# Expose the port
EXPOSE $PORT

# Command to run the app with gunicorn, setting very high keep-alive and timeout values
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "4", "--threads", "8", "--keep-alive", "900", "--timeout", "900"]