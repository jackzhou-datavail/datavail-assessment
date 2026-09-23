#!/bin/bash
APP_PORT="${DATABRICKS_APP_PORT:-${PORT:-8080}}"

# All resources are already built — serve status immediately.
python3 - << PYEOF
import os, http.server, socketserver, json

RESOURCES = {
    "genie_space_id": os.environ.get("GENIE_SPACE_ID", ""),
    "dashboard_id":   os.environ.get("DASHBOARD_ID", "")
}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "success",
            "message": "All resources built and ready.",
            "catalog": os.environ.get("DEMO_CATALOG", "main"),
            "schema": os.environ.get("DEMO_SCHEMA", "workspace_health_assessment"),
            "resources": RESOURCES,
        }, indent=2).encode())
    def log_message(self, *args): pass

class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

port = int(os.environ.get('DATABRICKS_APP_PORT', os.environ.get('PORT', 8080)))
print(f"Ready on port {port}", flush=True)
with ReuseTCPServer(('0.0.0.0', port), Handler) as httpd:
    httpd.serve_forever()
PYEOF
