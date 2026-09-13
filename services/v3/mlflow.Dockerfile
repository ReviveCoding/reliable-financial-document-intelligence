FROM python:3.11.16-slim
RUN pip install --no-cache-dir mlflow==3.4.0 psycopg2-binary==2.9.10 boto3==1.40.21
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "postgresql://rfdi:rfdi-dev-only@rfdi-postgres:5432/mlflow", "--artifacts-destination", "s3://mlflow-artifacts"]
