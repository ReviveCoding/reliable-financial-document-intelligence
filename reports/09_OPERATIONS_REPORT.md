# Operations Report

Measured locked-final in-memory B0 latency: P50 0.0587 ms, P95 0.0824 ms, P99 0.7730 ms; calculated throughput 12,021.6 docs/s. These exclude OCR, file I/O, queue, network, persistence, rendering, and cold start and must not be treated as service SLO evidence.

E18 replayed two requests to the SQLite state-machine fixture and produced one identity, one finalized record, and zero duplicate final outputs. Invalid transitions are tested. Worker restart, database outage, queue saturation, OOM, and Docker stack recovery were not executed because the service dependencies were absent.
