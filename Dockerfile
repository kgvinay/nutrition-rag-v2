FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY config/ config/

EXPOSE 8000

CMD ["uvicorn", "nutrition_rag.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
