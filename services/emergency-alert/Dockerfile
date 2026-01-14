FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 3005

# Set environment variables
ENV PORT=3005
ENV DAPR_HTTP_PORT=3505
ENV DAPR_GRPC_PORT=50006

# Run the application
CMD ["python", "app.py"]

