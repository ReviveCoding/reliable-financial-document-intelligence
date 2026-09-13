# V3 Infrastructure and Runtime Evidence

The real V3 Compose stack was executed with the Windows Docker CLI through WSL
interoperability on context `desktop-linux`. Docker Desktop 4.90.0 exposed a
Linux 29.7.2 engine and Compose 5.5.1. PostgreSQL, Redis, MinIO, MLflow, the API,
worker, and reviewer services all reached their declared healthy states; the
one-shot MinIO initializer exited successfully after creating the private
`mlflow-artifacts` bucket.

MLflow run `ebaf889519954ed387676f5a0a04e474` provides a cross-store persistence
probe. Direct PostgreSQL queries found the finished run, its parameter, and its
metric. Direct MinIO listing found the corresponding 47-byte artifact under the
run's artifact prefix. This is actual metadata/artifact persistence evidence,
not an inference from container configuration.

Controlled service interruptions produced the following observations:

- Redis: a forced-save key survived stop/start. The API remained healthy because
  the preserved application implementation uses a SQLite durable queue; Redis is
  not its active job transport. This limitation is retained rather than hidden.
- PostgreSQL: the MLflow run endpoint returned HTTP 503 during the stop, then HTTP
  200 after restart with the same run row present.
- MinIO: MLflow artifact retrieval returned HTTP 500 during the stop, then returned
  the exact artifact content after restart.

The Docker GPU probe used `nvidia/cuda:13.0.0-base-ubuntu24.04` with `--gpus all`
and saw one NVIDIA GeForce RTX 4090 Laptop GPU with 16,376 MiB. No multi-GPU claim
is made.

The API/reviewer behavioral probe created one unique document, verified duplicate
idempotency, observed worker completion, committed a review edit, checked both
reviewer endpoints, and checked Prometheus-format metrics. All seven checks passed.

Detailed machine-readable evidence is under `artifacts/v3/docker/` and
`artifacts/v3/runtime/docker_api_reviewer.json`.
