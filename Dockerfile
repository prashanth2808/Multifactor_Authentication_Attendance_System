# =========================================
# MFA – Face & Voice Attendance System
# =========================================

FROM python:3.10-slim

# Python runtime settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for:
# OpenCV, ONNX Runtime, audio, FFmpeg
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy ONLY requirements.txt (no missing files)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Default environment variables (override if needed)
ENV MONGODB_URI=mongodb://host.docker.internal:27017
ENV DB_NAME=face_attendance
ENV SIMILARITY_THRESHOLD=0.62
ENV LIVENESS_REQUIRED=false
ENV LOG_LEVEL=INFO

# Flask port
EXPOSE 5000

# Default command (Flask UI)
CMD ["python", "app.py"]
