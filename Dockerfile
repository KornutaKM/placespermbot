FROM python:3.12-slim

ARG PLACES_BUILD_SHA=unverified
LABEL org.opencontainers.image.revision=${PLACES_BUILD_SHA}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLACES_BUILD_SHA=${PLACES_BUILD_SHA}

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --no-cache-dir .

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-m", "app.healthcheck"]

CMD ["python", "-m", "app.main"]
