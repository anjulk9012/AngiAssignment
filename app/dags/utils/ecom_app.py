#!/usr/bin/env python3
"""
E-commerce Data Exporter (Local JSONL, partitioned)
- Public API: Fake Store API (https://fakestoreapi.com/)
- Entities: products, users, carts
- Derived: order_lines (flattened from carts)

Outputs under:
  {OUTDIR}/raw/ecommerce/dt=YYYY-MM-DD/hour=HH/{entity}_*.jsonl

Usage:
  python ecom_exporter.py --outdir ./data --dataset ecommerce --with-derived
  # or minimal
  python ecom_exporter.py
"""

from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import sys
import time
from typing import Dict, Iterable, List, Optional

import requests

# Defaults (override with env or CLI)
DEFAULT_BASE_URL = os.getenv("ECOM_BASE_URL", "https://fakestoreapi.com")
DEFAULT_DATASET = os.getenv("DATASET", "ecommerce")
DEFAULT_OUTDIR = os.getenv("OUTDIR", "./data")
DEFAULT_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
DEFAULT_SLEEP = float(os.getenv("HTTP_SLEEP", "0.25"))

ENTITIES = {
    "products": "/products",
    "users": "/users",
    "carts": "/carts",
}

session = requests.Session()
session.headers.update({"Accept": "application/json"})


def ensure_partition_dir(base_outdir: str, dataset: str) -> str:
    """Create partition path like: {out}/raw/{dataset}/dt=YYYY-MM-DD/hour=HH/"""
    now = dt.datetime.utcnow()
    parts = [
        base_outdir.rstrip("/"),
        "raw",
        dataset,
        f"dt={now.strftime('%Y-%m-%d')}",
        f"hour={now.strftime('%H')}",
    ]
    path = os.path.join(*parts)
    os.makedirs(path, exist_ok=True)
    return path


def get_json(url: str, timeout: int) -> list:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        # some endpoints might return single object
        data = [data]
    return data


def write_jsonl(dirpath: str, entity: str, rows: Iterable[dict]) -> str:
    fname = f"{entity}_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    fpath = os.path.join(dirpath, fname)
    count = 0
    with open(fpath, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
            count += 1
    print(f"Wrote {count:>5} {entity:<12} → {fpath}")
    return fpath


def derive_order_lines(carts: List[dict]) -> List[dict]:
    """
    Flatten carts into order_lines suitable for a fact table.
    cart schema (Fake Store):
      {
        "id": 5, "userId": 3, "date": "2020-03-02T00:00:00.000Z",
        "products": [{"productId":1,"quantity":4}, ...]
      }
    Produces rows:
      {
        "order_id": <cart id>,
        "order_ts": <timestamp>,
        "user_id": <userId>,
        "product_id": <productId>,
        "quantity": <qty>
      }
    """
    out = []
    for c in carts:
        order_id = c.get("id")
        user_id = c.get("userId")
        order_ts = c.get("date")
        for p in c.get("products", []):
            out.append({
                "order_id": order_id,
                "order_ts": order_ts,
                "user_id": user_id,
                "product_id": p.get("productId"),
                "quantity": p.get("quantity"),
            })
    return out


def main():
    ap = argparse.ArgumentParser(description="Export e-commerce (Fake Store API) data to local JSONL.")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    ap.add_argument("--dataset", default=DEFAULT_DATASET, help="Dataset name for output path")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR, help="Base output directory")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout seconds")
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Sleep between entity calls")
    ap.add_argument("--with-derived", action="store_true", help="Also emit derived order_lines from carts")
    args = ap.parse_args()

    try:
        part_dir = ensure_partition_dir(args.outdir, args.dataset)

        # 1) PRODUCTS
        products_url = f"{args.base_url}{ENTITIES['products']}"
        products = get_json(products_url, timeout=args.timeout)
        write_jsonl(part_dir, "products", products)
        time.sleep(args.sleep)

        # 2) USERS
        users_url = f"{args.base_url}{ENTITIES['users']}"
        users = get_json(users_url, timeout=args.timeout)
        write_jsonl(part_dir, "users", users)
        time.sleep(args.sleep)

        # 3) CARTS (orders)
        carts_url = f"{args.base_url}{ENTITIES['carts']}"
        carts = get_json(carts_url, timeout=args.timeout)
        write_jsonl(part_dir, "carts", carts)

        # 4) DERIVED (optional) FACT: order_lines
        if args.with_derived:
            order_lines = derive_order_lines(carts)
            write_jsonl(part_dir, "order_lines", order_lines)

        # Schema hints for modeling
        sample = {
            "dim_product": ["id (PK)", "title", "category", "price", "rating.rate", "rating.count"],
            "dim_user": ["id (PK)", "email", "username", "name.firstname", "name.lastname", "address.city"],
            "fact_order_line": ["order_id", "order_ts", "user_id (FK)", "product_id (FK)", "quantity"]
        }
        print("Suggested dims/facts:", json.dumps(sample, indent=2))

        print("\nDone. Partition:", part_dir.replace("\\", "/"))

    except requests.HTTPError as e:
        print(f"[HTTP ERROR] {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
