Here’s a full document you can drop in as `README.md` at the **root of your repo** (AngiAssignment). It pulls everything together: exporter app, MySQL schema, dbt, Airflow on Kubernetes, and GitLab CI/CD.

You can tweak naming (project name, paths) but this is ready-to-use.

---

# E-commerce Data Pipeline on Kubernetes (Airflow + dbt + MySQL)

## 1. Overview

This project implements a small but complete analytics pipeline:

1. **Data export application** (Python)

   * Pulls data from the **Fake Store API** (products, users, carts)
   * Writes partitioned **JSONL** files under `data/raw/ecommerce/...`

2. **Database layer (MySQL)**

   * Tables for `dim_product`, `dim_user`, and `fact_order_line`
   * Initialized via SQL migrations in `db/ecommerce`

3. **dbt project**

   * Models to transform raw JSON / staging tables into star-schema dimensions + fact
   * `dbt test`, `dbt run`, and `dbt docs generate`

4. **Orchestration with Airflow on Kubernetes (Minikube)**

   * Airflow deployed via Helm chart
   * DAGS + dbt project + SQL migrations loaded via GitSync from this repo
   * Single DAG runs:

     * Export job (Python)
     * DB migrations (MySQL)
     * dbt debug / test / run / docs

5. **GitLab CI/CD**

   * Build application image
   * Run dbt tests & models
   * Deploy to local K8s via kubectl/Helm
   * Generate dbt docs

---

## 2. Repository Layout

Root of the repo (simplified):

```text
.
├── Dockerfile                       # Custom Airflow/dbt image
├── README.md                        # This document
├── requirements.txt                 # Optional Python deps
├── ecom_app.py                      # Local copy of exporter (for reference)
│
├── app/
│   └── dags/
│       ├── ecom_exporter_dag.py     # Airflow DAG (export + dbt pipeline)
│       └── utils/
│           └── ecom_app.py          # Exporter used by Airflow
│
├── airflow-k8-dbt/
│   ├── dbt/
│   │   ├── dbt_project.yml
│   │   ├── profiles.yml
│   │   └── models/
│   │       ├── sources.yml
│   │       ├── staging/
│   │       │   ├── staging.yml
│   │       │   ├── stg_products.sql
│   │       │   ├── stg_users.sql
│   │       │   └── stg_order_lines.sql
│   │       └── marts/
│   │           ├── marts.yml
│   │           ├── dim_product.sql
│   │           ├── dim_user.sql
│   │           └── fact_order_line.sql
│   │
│   └── k8s/
│       └── airflow/
│           ├── helm/
│           │   └── values-mysql.yaml   # Airflow config (MySQL + GitSync)
│           ├── mysql/
│           │   └── mysql-deployment.yaml
│           └── scripts/
│               ├── deploy_airflow.sh
│               ├── port_forward_webserver.sh
│               └── uninstall_airflow.sh
│
├── db/
│   └── ecommerce/
│       ├── 0001_create_dim_product.sql
│       ├── 0002_create_dim_user.sql
│       └── 0003_create_fact_order_line.sql
│
├── data/
│   └── raw/
│       └── ecommerce/
│           └── dt=YYYY-MM-DD/hour=HH/   # Exported JSONL files (created at runtime)
│
└── .gitlab-ci.yml                  # GitLab CI pipeline (build/test/deploy/transform)
```

---

## 3. Data Export Application (Python)

Source file:

* `app/dags/utils/ecom_app.py` (invoked by Airflow)
* Local reference copy at repo root: `ecom_app.py`

Key behavior:

* Calls `https://fakestoreapi.com` endpoints:

  * `/products`  → product catalog
  * `/users`     → customers
  * `/carts`     → orders
* Writes partitioned JSONL:

```text
data/raw/ecommerce/dt=YYYY-MM-DD/hour=HH/products_*.jsonl
data/raw/ecommerce/dt=YYYY-MM-DD/hour=HH/users_*.jsonl
data/raw/ecommerce/dt=YYYY-MM-DD/hour=HH/carts_*.jsonl
data/raw/ecommerce/dt=YYYY-MM-DD/hour=HH/order_lines_*.jsonl
```

`order_lines` is derived by flattening the `products[]` array from each cart:

```json
{
  "order_id": 1,
  "order_ts": "2020-03-02T00:00:00.000Z",
  "user_id": 1,
  "product_id": 1,
  "quantity": 4
}
```

To run locally (outside Airflow):

```bash
python ecom_app.py --outdir ./data --dataset ecommerce --with-derived
```

---

## 4. Database Schemas / Migrations (MySQL)

All database initialization scripts live in:

* `db/ecommerce/`

Each numbered file is a migration (applied in order):

* `0001_create_dim_product.sql`
* `0002_create_dim_user.sql`
* `0003_create_fact_order_line.sql`

Example table definitions (simplified):

```sql
-- dim_product
CREATE TABLE IF NOT EXISTS dim_product (
  product_id      BIGINT PRIMARY KEY,
  title           VARCHAR(512),
  category        VARCHAR(128),
  price           DECIMAL(10,2),
  rating_rate     DECIMAL(3,2),
  rating_count    INT
);

-- dim_user
CREATE TABLE IF NOT EXISTS dim_user (
  user_id         BIGINT PRIMARY KEY,
  email           VARCHAR(255),
  username        VARCHAR(255),
  first_name      VARCHAR(128),
  last_name       VARCHAR(128),
  city            VARCHAR(128)
);

-- fact_order_line
CREATE TABLE IF NOT EXISTS fact_order_line (
  order_id        BIGINT,
  order_ts        DATETIME,
  user_id         BIGINT,
  product_id      BIGINT,
  quantity        INT,
  PRIMARY KEY (order_id, product_id),
  CONSTRAINT fk_fact_user    FOREIGN KEY (user_id)    REFERENCES dim_user(user_id),
  CONSTRAINT fk_fact_product FOREIGN KEY (product_id) REFERENCES dim_product(product_id)
);
```

These can be applied via:

* dbt models (preferred), or
* manual script execution via a MySQL client.

---

## 5. dbt Project

Location:

* `airflow-k8-dbt/dbt/`

Key files:

* `dbt_project.yml`

  * Project name, model paths, materialization config.
* `profiles.yml`

  * dbt profile pointing to the MySQL instance inside Kubernetes.

Example `profiles.yml` (MySQL):

```yaml
ecommerce:
  target: dev
  outputs:
    dev:
      type: mysql
      server: airflow-mysql.airflow.svc.cluster.local
      port: 3306
      user: root
      password: root
      schema: ecommerce
      database: ecommerce
      threads: 4
```

Models:

* `models/staging/`

  * `stg_products.sql`
  * `stg_users.sql`
  * `stg_order_lines.sql`
* `models/marts/`

  * `dim_product.sql`
  * `dim_user.sql`
  * `fact_order_line.sql`
* `sources.yml`, `staging.yml`, `marts.yml` define sources, tests, and relationships.

Typical dbt commands (from `airflow-k8-dbt/dbt`):

```bash
# Validate connection & config
DBT_PROFILES_DIR=. dbt debug

# Run tests
DBT_PROFILES_DIR=. dbt test

# Run models
DBT_PROFILES_DIR=. dbt run

# Generate documentation
DBT_PROFILES_DIR=. dbt docs generate
# Serve docs locally
DBT_PROFILES_DIR=. dbt docs serve --port 8081
```

---

## 6. Kubernetes Manifests

Location:

* `airflow-k8-dbt/k8s/airflow/`

### 6.1 MySQL Deployment

File: `mysql/mysql-deployment.yaml`

* Deploys a simple MySQL instance inside the `airflow` namespace:

  * Service: `airflow-mysql` (port 3306)
  * User: `airflow`
  * Password: `airflow_pass`
  * Database: `airflow`

### 6.2 Airflow Helm Values (MySQL + GitSync)

File: `helm/values-mysql.yaml`

Key points:

* Executor: CeleryExecutor (or KubernetesExecutor if explicitly set)
* Webserver: NodePort service
* Built-in Postgres: disabled
* External metadata DB: MySQL (`airflow-mysql` service)
* DAGs via GitSync from this repo

Example (simplified):

```yaml
executor: CeleryExecutor

webserver:
  service:
    type: NodePort

postgresql:
  enabled: false

data:
  metadataConnection:
    user: airflow
    pass: airflow_pass
    protocol: mysql
    host: airflow-mysql.airflow.svc.cluster.local
    port: 3306
    db: airflow
    sslmode: disable

dags:
  persistence:
    enabled: false

  gitSync:
    enabled: true
    repo: https://github.com/anjulk9012/AngiAssignment.git
    branch: main
    subPath: app/dags        # location of DAGs in repo
    wait: 10
    depth: 1
```

### 6.3 Helper Scripts

Under `scripts/`:

* `deploy_airflow.sh`

  * Creates namespace, applies MySQL manifest, installs/upgrades Airflow via Helm with `values-mysql.yaml`.
* `port_forward_webserver.sh`

  * Finds the webserver service or pod and port-forwards it to localhost (UI access).
* `uninstall_airflow.sh`

  * Removes the Airflow Helm release and MySQL resources.

---

## 7. GitLab CI/CD Configuration (`.gitlab-ci.yml`)

Place this file in the **repo root** (`.gitlab-ci.yml`).

Example pipeline with stages: **build**, **test**, **deploy**, **transform**:

```yaml
stages:
  - build
  - test
  - deploy
  - transform

variables:
  DOCKER_IMAGE: "$CI_REGISTRY_IMAGE/ecom-airflow"

# 1) Build custom Airflow image (with exporter + dbt)
build_image:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u "$CI_REGISTRY_USER" -p "$CI_REGISTRY_PASSWORD" "$CI_REGISTRY"
    - docker build -t "$DOCKER_IMAGE:$CI_COMMIT_SHORT_SHA" .
    - docker push "$DOCKER_IMAGE:$CI_COMMIT_SHORT_SHA"
  only:
    - main

# 2) dbt tests (optional: run outside K8s directly in CI)
dbt_test:
  stage: test
  image: python:3.12-slim
  before_script:
    - pip install dbt-core dbt-mysql
    - cd airflow-k8-dbt/dbt
  script:
    - DBT_PROFILES_DIR=. dbt debug
    - DBT_PROFILES_DIR=. dbt test
  only:
    - main

# 3) Deploy to local cluster (Minikube) using a shell runner
deploy_to_minikube:
  stage: deploy
  tags:
    - minikube-runner        # shell runner on your machine
  script:
    - cd airflow-k8-dbt/k8s/airflow
    - ./scripts/deploy_airflow.sh
  only:
    - main

# 4) Transform: run dbt (inside cluster via Airflow or direct exec)
dbt_run_in_cluster:
  stage: transform
  tags:
    - minikube-runner
  script:
    # Example: exec into dbt pod or run dbt via kubectl
    - kubectl exec -it -n airflow $(kubectl get pods -n airflow -l component=worker -o jsonpath='{.items[0].metadata.name}') -- \
        bash -c "cd /opt/airflow/dags/repo/airflow-k8-dbt/dbt && DBT_PROFILES_DIR=. dbt run"
  only:
    - main
```

### GitLab Setup (how to actually make this work)

1. **Enable Shared or Specific Runner**

   * Either use GitLab’s shared runners (for Docker build + dbt tests), **and**
   * Register a **shell runner on your local machine** (tagged `minikube-runner`) that:

     * Has `kubectl` installed
     * Can talk to your local Minikube cluster (`KUBECONFIG` configured)
     * Has access to Docker (if you want it to also build images)

2. **Register a Shell Runner (local)**

On your machine:

* Install GitLab Runner:

  ```bash
  # On macOS via Homebrew
  brew install gitlab-runner
  ```

* Register runner:

  ```bash
  gitlab-runner register
  ```

  During prompts:

  * GitLab URL: `https://gitlab.com/` (or your self-hosted URL)
  * Registration token: from GitLab → Settings → CI/CD → Runners → New runner.
  * Description: `minikube-runner`
  * Tags: `minikube-runner`
  * Executor: `shell`

  Ensure this runner’s shell environment has:

  * `kubectl` in PATH and configured to talk to Minikube (`kubectl config use-context minikube`)
  * Optional: `helm` if you want helm in pipeline.
  * `docker` if you also use it to build images.

3. **CI/CD Variables to Set in GitLab**

In GitLab → Project → Settings → CI/CD → Variables:

* `CI_REGISTRY_USER` / `CI_REGISTRY_PASSWORD`

  * Credentials to push images to GitLab Container Registry.
* (Optional) DB credentials if needed.
* (Optional) anything else you want to keep secret.

---

## 8. Airflow DAG – End-to-end Pipeline

DAG file:

* `app/dags/ecom_exporter_dag.py`

High-level behavior:

1. `export_task`:

   * `PythonOperator` calling `utils.ecom_app.main()`
   * Fetches data from Fake Store API and writes JSONL to `/opt/airflow/data` (or repo path).

2. `db_migrate_task` (optional):

   * `BashOperator` executing SQL from `db/ecommerce/*.sql` against MySQL.

3. `dbt_debug`, `dbt_test`, `dbt_run`, `dbt_docs` tasks:

   * `BashOperator` tasks like:

   ```bash
   cd /opt/airflow/dags/repo/airflow-k8-dbt/dbt && \
   DBT_PROFILES_DIR=. dbt debug
   DBT_PROFILES_DIR=. dbt test
   DBT_PROFILES_DIR=. dbt run
   DBT_PROFILES_DIR=. dbt docs generate
   ```

4. Dependencies:

```text
export_task -> db_migrate_task -> dbt_debug -> dbt_test -> dbt_run -> dbt_docs
```

Once GitSync pulls this DAG into Airflow:

* Open Airflow UI
* Unpause `ecom_exporter_dbt_pipeline` (or whatever DAG ID you use)
* Trigger a run and watch the tasks.

---

## 9. Architecture Diagram (Conceptual)

You can draw this in a tool and save as `docs/architecture.png`. Conceptually:

```text
         +------------------------+
         |   Fake Store API       |
         |  (products/users/carts)|
         +-----------+------------+
                     |
                     v
            [Data Exporter (Python)]
            ecom_app.py in Airflow
                     |
                     v
       JSONL files under /data/raw/ecommerce
                     |
                     v
          +------------------------------+
          |        MySQL Database        |
          |   dim_product / dim_user /   |
          |      fact_order_line         |
          +--------------+---------------+
                         |
                         v
                 [dbt (inside Airflow)]
               staging -> marts models
                         |
                         v
              Analytics-ready schema
                         |
                         v
                BI / Sample Queries
```

---

## 10. Sample Data & Queries

**Sample Data**:

* Exporter pulls real sample data from `https://fakestoreapi.com`.
* The JSONL outputs are lightweight and stable enough for repeatable tests.

**Sample SQL Queries (after dbt run)**:

```sql
-- Top 5 products by total quantity sold
SELECT
  p.title,
  SUM(f.quantity) AS total_qty
FROM fact_order_line f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.title
ORDER BY total_qty DESC
LIMIT 5;

-- Customer order count
SELECT
  u.username,
  COUNT(DISTINCT f.order_id) AS order_count
FROM fact_order_line f
JOIN dim_user u ON f.user_id = u.user_id
GROUP BY u.username
ORDER BY order_count DESC;
```

---

## 11. Step-by-step: Reproducing Locally

1. **Prerequisites**

   * Docker Desktop
   * Minikube
   * kubectl, helm
   * Python 3.11+ (for any local testing)
   * Git

2. **Start Minikube**

```bash
minikube start --driver=docker --cpus=4 --memory=8192
```

3. **Build and (optionally) load image into Minikube**

```bash
docker build -t ecom-airflow:0.2.0 .
minikube image load ecom-airflow:0.2.0
```

4. **Deploy MySQL + Airflow**

```bash
cd airflow-k8-dbt/k8s/airflow
./scripts/deploy_airflow.sh
```

5. **Access Airflow UI**

```bash
./scripts/port_forward_webserver.sh
# then open http://localhost:8080
```

6. **Run the pipeline**

* In Airflow UI:

  * Unpause the `ecom_exporter_dbt_pipeline` DAG.
  * Trigger a DAG run.
* Monitor logs for:

  * Successful export
  * dbt debug/test/run/docs

7. **View dbt docs**

* Either via Airflow dbt_docs task output (mounted location), or:
* Run locally:

  ```bash
  cd airflow-k8-dbt/dbt
  DBT_PROFILES_DIR=. dbt docs serve --port 8081
  ```

  Open `http://localhost:8081`.
