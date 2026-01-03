# VAL - Voice Assistant Learning Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for voice processing
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p logs memory models voice

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port if needed (for web interface)
EXPOSE 8000

# Run the application
CMD ["python", "val.py"]