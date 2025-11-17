# Start from official Airflow image
FROM apache/airflow:3.0.2

# ---- OS deps (optional, but mysql client can be useful) ----
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# ---- Python deps: install as airflow user (required by this image) ----
USER airflow

RUN pip install --no-cache-dir \
      requests \
      dbt-core \
      dbt-mysql \
      protobuf
