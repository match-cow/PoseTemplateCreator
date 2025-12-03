FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY web_app.py ./

COPY assets/ ./assets/

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "web_app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true", "--server.runOnSave", "false"]