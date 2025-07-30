# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# --- THIS IS THE FIX ---
# Install git, which is required for installing packages from GitHub
RUN apt-get update && apt-get install -y git
# --- END OF FIX ---

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Command to run your application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]


