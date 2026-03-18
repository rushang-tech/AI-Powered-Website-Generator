import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting AI Website Generator Server...")
    port = int(os.environ.get("PORT", "5001"))
    debug = os.environ.get("FLASK_DEBUG", "").strip() == "1"
    app.run(host="0.0.0.0", debug=debug, port=port)
