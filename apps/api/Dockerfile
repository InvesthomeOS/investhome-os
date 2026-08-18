# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libcairo2-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

FROM base AS runner
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh \
    && mkdir -p /var/lib/investhome/documents \
    && chown -R appuser:appuser /var/lib/investhome
USER root
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
