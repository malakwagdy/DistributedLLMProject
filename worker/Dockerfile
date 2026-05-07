# Use the same Python version for consistency across the cluster
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Set environment variables
# Essential for seeing "Worker Started" logs in real-time
ENV PYTHONUNBUFFERED=1

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app (include worker/rag_data/ if present after `python build_index.py`, or set RAG_S3_* at runtime).
COPY . .

# Start the worker script
CMD ["python", "worker.py"]