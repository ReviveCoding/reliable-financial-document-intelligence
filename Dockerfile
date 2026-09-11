FROM python:3.10-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY services ./services
RUN pip install --no-cache-dir ".[api]"
ENV PYTHONPATH=/app/src
