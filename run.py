import os
from app.main import app

if __name__ == "__main__":
    from app.dev_reload import enable_live_reload, watched_files
    from pathlib import Path

    root = Path(__file__).resolve().parent
    live_reload = os.getenv("LIVE_RELOAD", "1") == "1"
    if live_reload:
        enable_live_reload(app, root)
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8080")),
            debug=False, use_debugger=False, use_reloader=live_reload,
            extra_files=[str(p) for p in watched_files(root)] if live_reload else None)
