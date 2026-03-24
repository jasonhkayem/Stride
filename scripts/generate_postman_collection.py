import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root is importable when running from scripts/.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app

WRITE_METHODS = {"POST", "PUT", "PATCH"}
SKIP_METHODS = {"HEAD", "OPTIONS"}


def to_postman_path(flask_path: str) -> str:
    # Convert Flask params (/users/<id>) to Postman style (/users/:id)
    return flask_path.replace("<", ":").replace(">", "")


def request_item(method: str, path: str, base_url_var: str) -> dict:
    postman_path = to_postman_path(path)
    raw_url = f"{{{{{base_url_var}}}}}{postman_path}"

    request = {
        "method": method,
        "header": [],
        "url": raw_url,
        "description": f"Auto-generated from Flask route: {path}",
    }

    if method in WRITE_METHODS:
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": "{}",
            "options": {"raw": {"language": "json"}},
        }

    return {
        "name": f"{method} {postman_path}",
        "request": request,
        "response": [],
    }


def build_collection(base_url: str) -> dict:
    groups = defaultdict(list)

    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods))):
        methods = sorted(m for m in rule.methods if m not in SKIP_METHODS)
        if not methods:
            continue

        parts = [p for p in rule.rule.split("/") if p]
        group = parts[0] if parts else "root"

        for method in methods:
            groups[group].append(request_item(method, rule.rule, "baseUrl"))

    items = []
    for group in sorted(groups.keys()):
        items.append({"name": group, "item": groups[group]})

    return {
        "info": {
            "name": "Final Year Project API",
            "description": "Auto-generated from Flask routes in app.url_map",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": base_url,
                "type": "string",
            }
        ],
        "item": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Postman collection from Flask routes")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base URL for requests")
    parser.add_argument(
        "--output",
        default="postman_collection.json",
        help="Output collection JSON path",
    )
    args = parser.parse_args()

    collection = build_collection(args.base_url)
    output_path = Path(args.output)
    output_path.write_text(json.dumps(collection, indent=2), encoding="utf-8")

    total_requests = sum(len(group["item"]) for group in collection["item"])
    print(f"Generated {output_path} with {total_requests} requests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
