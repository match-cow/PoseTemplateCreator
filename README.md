# Pose Template Creator

A Streamlit web application for creating pose templates from 3D models.

## Running Locally

```bash
uv sync
uv run streamlit run app.py
```

## Running with Docker

### Using Docker Compose (Recommended)

```bash
docker-compose up --build
```

This will build the image and start the container, mounting the `assets` and `object_models` directories for live updates.

### Using Docker Directly

```bash
docker build -t pose-template-creator . && docker run -p 8502:8502 pose-template-creator
```

Access the app at http://localhost:8502