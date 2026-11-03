import tempfile
import unittest
from pathlib import Path
from flask import Flask
from app.dev_reload import enable_live_reload


class LiveReloadTests(unittest.TestCase):
    def test_revision_injection_and_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'templates').mkdir()
            page = root / 'templates' / 'index.html'
            page.write_text('first')
            app = Flask(__name__)
            app.add_url_rule('/', view_func=lambda: '<html><body>Hello</body></html>')
            self.assertEqual(Flask('disabled').test_client().get('/__dev/revision').status_code, 404)
            enable_live_reload(app, root)
            client = app.test_client()
            html = client.get('/')
            self.assertIn(b'data-revision=', html.data)
            self.assertEqual(html.headers['Cache-Control'], 'no-store')
            first = client.get('/__dev/revision').json['revision']
            self.assertEqual(first, client.get('/__dev/revision').json['revision'])
            page.write_text('second')
            second = client.get('/__dev/revision').json['revision']
            self.assertNotEqual(first, second)
            (root / 'local.sqlite3').write_text('ignored')
            self.assertEqual(second, client.get('/__dev/revision').json['revision'])
            page.unlink()
            self.assertNotEqual(second, client.get('/__dev/revision').json['revision'])
            with client.get('/__dev/live-reload.js') as script:
                self.assertEqual(script.status_code, 200)


if __name__ == '__main__':
    unittest.main()
