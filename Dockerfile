FROM python:3.11-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY autoppt ./autoppt
COPY templates ./templates

RUN python -m pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel --outdir /dist

FROM python:3.11-slim

LABEL maintainer="yeasy@example.com"
LABEL description="AutoPPT - AI-Powered Presentation Generator"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime system dependencies for thumbnails (LibreOffice + Poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /tmp/*.whl \
    && rm -f /tmp/*.whl

# Streamlit needs a script path; copy the UI source only.
COPY --chown=appuser:appuser autoppt /app/autoppt

RUN mkdir -p /app/output && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)"

CMD ["python", "-m", "streamlit", "run", "/app/autoppt/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
