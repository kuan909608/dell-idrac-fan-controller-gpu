# Use Python 3.13 as base image
FROM python:3.13-slim

# Set Python to output logs without buffering for real-time log visibility
ENV PYTHONUNBUFFERED=1

# Prepare a read-only mount point for an operator-managed known_hosts file.
RUN install -d -m 0700 /root/.ssh

# Install required system packages
# build-essential: for compiling C extensions (needed by pysensors)
# libsensors4-dev: hardware sensor library (needed by pysensors)
# ipmitool: for IPMI sensor support
# openssh-client: for remote operations
RUN apt-get update && apt-get install -y ipmitool && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
ENV FAN_CONTROL_CONFIG=/config/fan_control_config.yaml

# Copy requirements.txt and install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the files required by the controller at runtime.
COPY main.py config_loader.py control_policy.py fan_controller.py lifecycle.py ./
COPY monitoring_web.py state.py temp_monitor.py utils.py ./

# Default command to run main program
CMD ["python", "./main.py"]
