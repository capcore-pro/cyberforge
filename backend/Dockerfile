FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    # TODO: ajouter gcc libcairo2-dev pkg-config quand svglib sera réactivé
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps || playwright install chromium

COPY backend/package.json backend/package-lock.json ./
RUN npm ci --omit=dev

COPY backend/. .

# Template vitrine (Next.js) requis pour le scaffold en prod
COPY templates/vitrine-next ./templates/vitrine-next

# Railway injecte PORT (expansion shell requise)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
