# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for image processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY hand_image_server.py .
COPY poker_viz/ ./poker_viz/
COPY poker_table_visualizer.py .
COPY clear_spot_solution_json.py .
COPY fonts/ ./fonts/
COPY cards-images/ ./cards-images/
COPY poker_solutions/ ./poker_solutions/
COPY flow_logo.png .
COPY avatar.png .

# Create directory for temporary files
RUN mkdir -p /tmp/hand_images

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    chown -R app:app /tmp/hand_images

# Switch to non-root user
USER app

# Expose port
EXPOSE 8777

# Set environment variables
ENV FLASK_APP=hand_image_server.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8777/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8777", "--workers", "4", "--timeout", "120", "--worker-class", "sync", "hand_image_server:app"]