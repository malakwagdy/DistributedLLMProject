# Use a slim version of Python 3.12 for better performance and smaller size
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables
# This ensures Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Copy only the requirements first (Best Practice: Layer Caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the gateway code
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the Gateway using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]