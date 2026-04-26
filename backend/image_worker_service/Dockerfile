FROM python:3.11-slim

WORKDIR /app

# Install only image worker deps
COPY image_worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY image worker + shared
COPY image_worker_service/ ./image_worker_service/
COPY shared/ ./shared/

# Run image worker job
CMD ["python", "image_worker_service/downloader.py"]