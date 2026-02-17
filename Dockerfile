FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY app.py ./

COPY assets/ ./assets/

COPY .streamlit/ ./.streamlit/

EXPOSE 8502

CMD ["uv", "run", "streamlit", "run", "app.py"]