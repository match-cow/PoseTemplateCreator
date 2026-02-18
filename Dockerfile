FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
# RUN uv sync --frozen --no-install-project
RUN uv pip install --system -r pyproject.toml

COPY app.py ./
COPY assets/ ./assets/
COPY .streamlit/ ./.streamlit/

EXPOSE 8502

CMD ["streamlit", "run", "app.py"]