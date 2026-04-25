FROM python:3.11-slim

WORKDIR /app

# Install only scraper deps
COPY athlete_image_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY scraper + shared
COPY athlete_image_service/ ./athlete_image_service/
COPY shared/ ./shared/

# Run scraper job
CMD ["python", "athlete_image_service/scrape_fighter_images.py"]