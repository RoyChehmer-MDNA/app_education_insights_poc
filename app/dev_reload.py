"""Dependency-free live reload, enabled only by the local development launcher."""
import hashlib
from pathlib import Path
from uuid import uuid4
from flask import jsonify, request, send_file


def watched_files(root):
    root = Path(root)
    files = [root / 'run.py']
    for folder, extensions in (('app', {'.py', '.json', '.js'}),
                               ('templates', {'.html'}),
                               ('static', {'.css', '.js'})):
        files.extend(p for p in (root / folder).rglob('*') if p.suffix in extensions and p.is_file())
    return sorted(files)


def enable_live_reload(app, root=None):
    root = Path(root or Path(app.root_path).parent)
    boot = uuid4().hex
    app.config.update(TEMPLATES_AUTO_RELOAD=True, SEND_FILE_MAX_AGE_DEFAULT=0)
    app.jinja_env.auto_reload = True

    def revision():
        digest = hashlib.sha256(boot.encode())
        for path in watched_files(root):
            try:
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
            except FileNotFoundError:
                # Editors sometimes replace files atomically during a save.
                continue
        return digest.hexdigest()

    @app.get('/__dev/revision')
    def dev_revision():
        return jsonify(revision=revision())

    @app.get('/__dev/live-reload.js')
    def dev_script():
        return send_file(Path(__file__).with_name('live_reload.js'), mimetype='text/javascript')

    @app.after_request
    def inject_reload(response):
        response.headers['Cache-Control'] = 'no-store'
        if response.mimetype == 'text/html' and not response.direct_passthrough and request.method != 'HEAD':
            script = f'<script src="/__dev/live-reload.js" data-revision="{revision()}" defer></script>'
            response.set_data(response.get_data(as_text=True).replace('</body>', script + '</body>'))
        return response
