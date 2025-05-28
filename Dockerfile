# Use Python 3.11 (Debian Bullseye) as base image
FROM python:3.11-bullseye

# Set Python to output logs without buffering for real-time log visibility
ENV PYTHONUNBUFFERED=1

# Configure SSH to avoid blocking on first connection
RUN mkdir /root/.ssh && echo "Host *\n  StrictHostKeyChecking accept-new" >/root/.ssh/config

# Install required system packages
# build-essential: for compiling C extensions (needed by pysensors)
# libsensors4-dev: hardware sensor library (needed by pysensors)
# ipmitool: for IPMI sensor support
# openssh-client: for remote operations
RUN apt-get update &&
    apt-get install -y \
        build-essential \
        libsensors4-dev \
        ipmitool \
        openssh-client &&
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements.txt and install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Default command to run main program
CMD ["python", "./fan_control.py"]
