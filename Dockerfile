# Debug version of Dockerfile with more verbose logging
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for better debugging
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Install system dependencies with more verbose output
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && echo "System dependencies installed successfully"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with verbose output
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --verbose -r requirements.txt && \
    echo "Python dependencies installed successfully" && \
    pip list

# Copy application code
COPY sigma_mcp_server.py .

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcp && \
    chown -R mcp:mcp /app
USER mcp

# Add a test script to verify the server can start
RUN python -c "import sys; print(f'Python version: {sys.version}'); import asyncio, httpx, mcp; print('All imports successful')"

# Default command with streamable-http transport for deployment
CMD ["python", "-u", "sigma_mcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]