FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/. .

# Template vitrine (Next.js) requis pour le scaffold en prod
COPY templates/vitrine-next ./templates/vitrine-next

# Railway injecte PORT (expansion shell requise)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
