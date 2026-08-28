import sys
sys.path.insert(0, ".")
from app.main import create_application
from fastapi.routing import APIRoute
from starlette.routing import Route, WebSocketRoute

app = create_application()

def get_all_routes(routes, prefix=""):
    result = []
    for r in routes:
        if isinstance(r, (APIRoute, Route)):
            methods = [m for m in getattr(r, "methods", ["GET"]) if m not in ("HEAD", "OPTIONS")]
            for method in methods:
                tags = getattr(r, "tags", [])
                tag = tags[0] if tags else "General"
                summary = getattr(r, "summary", "") or getattr(r, "name", "")
                result.append((tag, method, prefix + r.path, summary))
        elif isinstance(r, WebSocketRoute):
            tags = getattr(r, "tags", [])
            tag = tags[0] if tags else "WebSockets"
            result.append((tag, "WS", prefix + r.path, getattr(r, "name", "")))
        elif hasattr(r, "router"):
            result.extend(get_all_routes(r.router.routes, prefix=prefix + (getattr(r, "prefix", "") or "")))
    return result

# Or from OpenAPI paths
openapi = app.openapi()
openapi_paths = openapi.get("paths", {})

print(f"OpenAPI Paths Count: {len(openapi_paths)}")
endpoint_count = 0
for path, methods_dict in openapi_paths.items():
    for method, details in methods_dict.items():
        if method.lower() in ["get", "post", "put", "patch", "delete", "websocket"]:
            endpoint_count += 1

print(f"Total API operations in OpenAPI schema: {endpoint_count}")

from collections import defaultdict
grouped = defaultdict(list)

for path, methods_dict in openapi_paths.items():
    for method, details in methods_dict.items():
        if method.lower() in ["get", "post", "put", "patch", "delete", "websocket"]:
            tags = details.get("tags", ["Other"])
            tag = tags[0] if tags else "Other"
            summary = details.get("summary", "")
            grouped[tag].append((method.upper(), path, summary))

for tag, routes in sorted(grouped.items()):
    print(f"\n### {tag} ({len(routes)} endpoint{'s' if len(routes) > 1 else ''})")
    for method, path, summary in sorted(routes, key=lambda x: (x[1], x[0])):
        print(f"- `{method:<6} {path}` — {summary}")
