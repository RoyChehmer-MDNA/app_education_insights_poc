import os
import re
from uuid import uuid4
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from .data import summary, allowed_ids
from .store import Store
from .orchestrator import Orchestrator, import_csv

USER = 'demo-supervisor'
DEFAULT_PROFILE = {'display_name': 'מירב לוי', 'role': 'מפקחת יסודי', 'district': 'חיפה'}


def create_app(config=None):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.update(MAX_CONTENT_LENGTH=1024 * 1024,
                      DATABASE=str(Path(app.instance_path) / 'local.sqlite3'),
                      SOURCES_PATH=str(Path(__file__).with_name('approved_sources.json')))
    app.config.update(config or {})
    # External integrations are deliberately disabled for this phase.
    if os.getenv('DATA_MODE', 'demo') != 'demo' or os.getenv('LLM_MODE', 'demo') not in ('demo', 'local'):
        raise RuntimeError('External integrations are disabled; use DATA_MODE=demo and LLM_MODE=local')
    store = Store(app.config['DATABASE'])
    agent = Orchestrator(store, app.config['SOURCES_PATH'])
    app.extensions.update(local_store=store, orchestrator=agent)

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError('Expected a JSON object')
        return value

    def conversation(value):
        if value is None:
            return str(uuid4())
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
            raise ValueError('Invalid conversation ID')
        return value

    @app.before_request
    def local_origin():
        # Prevent cross-site browser writes to the local demo database.
        origin = request.headers.get('Origin')
        if request.method in ('POST', 'PATCH', 'DELETE') and origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='cross_origin_write_denied'), 403

    @app.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(PermissionError)
    def denied(exc):
        return jsonify(error='access_denied'), 403

    @app.errorhandler(Exception)
    def failed(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.name), exc.code
        app.logger.exception('local backend failure')
        return jsonify(error='backend_unavailable'), 503

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.get('/content-portal')
    def content_portal():
        source = Path(app.root_path).parent / 'original_mockup_reference.html'
        html = source.read_text(encoding='utf-8')
        html = html.replace('</head>', '<script src="/static/theme.js"></script><link rel="stylesheet" href="/static/theme.css"><link rel="stylesheet" href="/static/portal-embed.css"></head>')
        html = html.replace('משל״ט · שולחן עבודה למפקח — אב-טיפוס', 'משל״ט · עולמות תוכן')
        html = html.replace('נתוני ציונים (תל״פ) עדיין לא מחוברים למערכת', 'נתוני הישגים')
        html = html.replace('</body>', '<script src="/static/portal-embed.js"></script></body>')
        return app.response_class(html, mimetype='text/html')

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', llm_mode='local', data_mode='local', demo_identity=True, external_integrations=False)

    @app.get('/api/dashboard')
    def dashboard():
        rows = agent.rows(USER)
        return jsonify(rows=rows, summary=summary(rows), demo_identity=True,
                       source='uploaded_csv' if store.get(USER, 'attendance') is not None else 'demo_data')

    @app.post('/api/chat')
    def chat():
        data = body()
        school = data.get('school_id')
        if school is not None and not isinstance(school, str):
            raise ValueError('Invalid school ID')
        cid = conversation(data.get('conversation_id'))
        if data.get('reset_context') is True:
            store.put(USER, 'context:' + cid, {})
        return jsonify(agent.run(data.get('question'), USER, cid, school))

    @app.get('/api/conversations/<cid>')
    def history(cid):
        return jsonify(messages=store.history(USER, conversation(cid)))

    @app.route('/api/profile', methods=['GET', 'PATCH'])
    def profile():
        if request.method == 'PATCH':
            data = body()
            if set(data) - {'display_name', 'role', 'district'} or any(not isinstance(v, str) or len(v) > 120 for v in data.values()):
                raise ValueError('Invalid profile fields')
            store.put(USER, 'profile', {**store.get(USER, 'profile', {}), **data})
        return jsonify(profile={**DEFAULT_PROFILE, **store.get(USER, 'profile', {})},
                       school_count=len(allowed_ids(USER)), demo_identity=True)

    @app.get('/api/gaps')
    def gaps():
        return jsonify(gaps=[g for g in store.gaps(USER) if g['school'] in allowed_ids(USER)])

    @app.patch('/api/gaps/<school>')
    def gap_update(school):
        if school not in allowed_ids(USER):
            raise PermissionError()
        status = body().get('status')
        if status not in ('open', 'in_progress', 'resolved'):
            raise ValueError('Invalid status')
        if not store.update_gap(USER, school, status):
            return jsonify(error='gap_not_found'), 404
        return jsonify(status=status)

    @app.post('/api/files/attendance')
    def upload():
        file = request.files.get('file')
        if not file or not file.filename.lower().endswith('.csv'):
            raise ValueError('Upload a UTF-8 .csv file')
        rows = import_csv(file.read(), USER)
        store.put(USER, 'attendance', rows)
        return jsonify(imported=len(rows), source='uploaded_csv', summary=summary(rows))

    @app.delete('/api/files/attendance')
    def reset_data():
        store.put(USER, 'attendance', None)
        return jsonify(source='demo_data')

    @app.get('/reports/attendance')
    def report():
        rows = agent.rows(USER)
        return render_template('report.html', rows=rows, stats=summary(rows),
                               source='CSV' if store.get(USER, 'attendance') is not None else 'נתוני הדגמה')

    return app


app = create_app()
