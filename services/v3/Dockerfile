FROM python:3.11.16-slim
WORKDIR /app
COPY src /app/src
COPY services/v3 /app/services/v3
RUN pip install --no-cache-dir fastapi==0.116.1 uvicorn==0.35.0 pydantic==2.11.7 python-multipart==0.0.20 redis==6.4.0
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "services.v3.api:app", "--host", "0.0.0.0", "--port", "8000"]
