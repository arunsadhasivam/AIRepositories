# Use an official Python base image
FROM python:3.11-slim

ENV SETUPTOOLS_USE_DISTUTILS=stdlib
ENV PYTHONPATH=/usr/lib/python3/dist-packages

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    python3-setuptools \
    build-essential

RUN pip install --upgrade pip

# Install setuptools and wheel
RUN pip install --upgrade setuptools wheel
# Update pip and install setuptools

# Explicitly exclude the problematic logging package
RUN pip install python-dotenv --no-deps
# Set the working directory in the container
WORKDIR /app

# Copy the application code
COPY requirements.txt .


# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

#COPY . .
COPY app.py .
# Expose the port Flask runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]