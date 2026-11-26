FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/app ./apps/api/app

WORKDIR /app/apps/api
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
