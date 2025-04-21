# Use an official Python base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the application code
#COPY requirements.txt .


# Install dependencies
#RUN pip install --no-cache-dir -r requirements1.txt
#COPY . .
COPY app.py .
# Expose the port Flask runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]