FROM python:3.12-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_THREAD_LIMIT=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng postgresql-client ca-certificates gosu fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home --uid 10001 palco && mkdir -p /var/data/media /app/staticfiles && chown -R palco:palco /app /var/data
EXPOSE 10000
ENTRYPOINT ["bash", "scripts/entrypoint.sh"]
CMD ["bash", "scripts/start.sh"]
