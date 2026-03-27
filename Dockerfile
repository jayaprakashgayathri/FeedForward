# ─────────────────────────────────────────────────────────────
# Stage 1: builder — install all Python deps into /install
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Build-time deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────
# Stage 2: runtime — lean final image
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Runtime lib for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY --chown=appuser:appuser . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

USER appuser

EXPOSE 5000

ENTRYPOINT ["sh", "entrypoint.sh"]
