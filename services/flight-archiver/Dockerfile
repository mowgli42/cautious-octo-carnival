FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 3004

# Set environment variables for Dapr
ENV DAPR_HTTP_PORT=3504
ENV DAPR_GRPC_PORT=50004

# Run the application
CMD ["python", "app.py"]

