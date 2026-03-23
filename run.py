import os

from app import create_app
from app.server_runtime import resolve_bind_port

app = create_app()

if __name__ == '__main__':
    selection = resolve_bind_port()
    if selection.auto_selected:
        print(
            f"Port {selection.requested_port} is already in use. "
            f"Starting AI Website Generator Server on http://localhost:{selection.port} instead..."
        )
    else:
        print(f"Starting AI Website Generator Server on http://localhost:{selection.port}...")
    debug = os.environ.get("FLASK_DEBUG", "").strip() == "1"
    app.run(host="0.0.0.0", debug=debug, port=selection.port)
