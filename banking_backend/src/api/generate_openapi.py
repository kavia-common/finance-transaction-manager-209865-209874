import json
import os

# Ensure app and routers are loaded
from src.api.main import app  # noqa: F401

# Generate and write OpenAPI schema
openapi_schema = app.openapi()

output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
