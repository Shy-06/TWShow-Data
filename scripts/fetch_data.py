#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data.json"
URL_TEMPLATE = "http://twshow.zjut.edu.cn/api/web/getActivityList?token={token}"
HEADERS = {"Content-Type": "application/json"}
PAYLOAD = {"activityName": "", "page": 1, "size": 10000}


def extract_items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return payload
        raise ValueError("Unexpected list payload; expected list of objects.")
    if isinstance(payload, dict):
        for key in ("data", "rows", "list", "result", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    return value
                raise ValueError(f"Unexpected items under '{key}'.")
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("records", "list", "rows"):
                value = data.get(key)
                if isinstance(value, list):
                    if all(isinstance(item, dict) for item in value):
                        return value
                    raise ValueError(f"Unexpected items under 'data.{key}'.")
    raise ValueError("Unexpected response shape; expected list of objects in response.")


def main() -> None:
    token = os.getenv("TW_SHOW_TOKEN")
    if not token:
        raise SystemExit("Token is required. Set TW_SHOW_TOKEN.")

    url = URL_TEMPLATE.format(token=token)
    try:
        response = requests.post(url, headers=HEADERS, json=PAYLOAD, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request failed: {exc.__class__.__name__}") from None

    if response.status_code >= 400:
        raise RuntimeError(f"Request failed with status {response.status_code}")

    payload = response.json()
    items = extract_items(payload)
    DATA_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
