FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# RUN uv sync --frozen --no-install-project
RUN uv pip install --system -r pyproject.toml

COPY app.py ./
COPY assets/ ./assets/
COPY .streamlit/ ./.streamlit/

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8502/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]