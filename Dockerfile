FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends chromium fonts-noto-core fonts-noto-cjk libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY . /app
ENV PYTHONPATH=/app/backend STORAGE_DIR=/app/storage CHROMIUM_COMMAND=chromium
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8000"]
