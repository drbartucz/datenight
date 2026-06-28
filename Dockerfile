FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip list

# Copy source code
COPY . .

# Expose port and run server
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python -c 'import main; print(\"Import OK\")' && uvicorn main:app --host 0.0.0.0 --port $PORT"]
