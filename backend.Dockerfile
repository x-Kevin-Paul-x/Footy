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

# Create report directories
RUN mkdir -p /app/reports/match_reports /app/reports/season_reports /app/reports/transfer_logs /app/reports/recordings /app/reports/ml_reports

# Expose API port
EXPOSE 5001

# Command to run the application
CMD ["uvicorn", "api_fastapi:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "5001"]
