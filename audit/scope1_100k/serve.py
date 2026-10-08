"""Run the real Flask app (threaded dev server) on an isolated, seeded database.

python serve.py <db_path> <port>
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from harness import boot  # noqa: E402

if __name__ == "__main__":
    db_path, port = sys.argv[1], int(sys.argv[2])
    app = boot(db_path, fresh=True)
    with app.app_context():
        from routes.auth import load_settings_from_db

        load_settings_from_db()
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)
