# ==========================================================
# KB-Geoid Telegram Bot - Multi-stage Production Dockerfile
# ==========================================================
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libproj-dev \
    proj-data \
    proj-bin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal runtime image
FROM python:3.13-slim AS runner

WORKDIR /app

# Install runtime PROJ libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libproj-dev \
    proj-data \
    proj-bin \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root app user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/.proj_cache && \
    chown -R appuser:appuser /app

# Copy python packages from builder stage
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=7860

# Copy application source code
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:7860/ || exit 1

CMD ["python", "app/main.py"]
