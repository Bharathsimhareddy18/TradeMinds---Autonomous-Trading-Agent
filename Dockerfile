FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Add local bin to path early
ENV PATH="/home/apiuser/.local/bin:$PATH"

# Create a non-root user for security (Industry standard for EC2)
RUN useradd -m -u 1000 apiuser
WORKDIR /app

# 1. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies (Cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# 3. Create cache folder and assign strict ownership (Replaces unsafe 777)
RUN mkdir -p /app/cache && chown -R apiuser:apiuser /app

# 4. Copy app code and set ownership
COPY --chown=apiuser:apiuser app/ /app/app/

# Switch to the secure non-root user
USER apiuser

# Expose the standard FastAPI port
EXPOSE 8000

# Run uvicorn on port 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]