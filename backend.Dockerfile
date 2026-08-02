FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend /app/
COPY data /app/data

# Create report directories
RUN mkdir -p /app/reports/match_reports /app/reports/season_reports /app/reports/transfer_logs

# Expose API port
EXPOSE 5001

# Command to run the application
CMD ["uvicorn", "src.api_fastapi:app", "--host", "0.0.0.0", "--port", "5001"]
