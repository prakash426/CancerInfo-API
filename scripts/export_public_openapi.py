"""Export the current public API contract without administrative routes."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.main import app


def build_public_openapi():
    spec = app.openapi().copy()
    spec["paths"] = {
        path: operation for path, operation in spec["paths"].items()
        if not path.startswith("/v1/admin/")
    }
    schemas = spec["components"]["schemas"]
    referenced = set()

    def collect(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref.rsplit("/", 1)[-1]
                if name not in referenced:
                    referenced.add(name)
                    collect(schemas[name])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(spec["paths"])
    spec["components"] = {"schemas": {
        name: schema for name, schema in schemas.items() if name in referenced
    }}
    spec["servers"] = [{"url": "https://cancerinfo-api.onrender.com"}]
    return spec


if __name__ == "__main__":
    target = Path("rapidapi/rapidapi-openapi.json")
    target.write_text(json.dumps(build_public_openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote public API contract to {target}")
