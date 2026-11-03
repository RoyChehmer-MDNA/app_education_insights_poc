import io
import json
import tempfile
import unittest
from pathlib import Path
from app.main import create_app


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sources = root / 'sources.json'
        self.sources.write_text('[]', encoding='utf-8')
        self.config = {'TESTING': True, 'DATABASE': str(root / 'test.db'), 'SOURCES_PATH': str(self.sources)}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def upload(self, value):
        return self.client.post('/api/files/attendance', data={'file': (io.BytesIO(value.encode('utf-8')), 'test.csv')})

    def test_persistent_workflow(self):
        self.assertEqual(self.client.get('/api/health').json['external_integrations'], False)
        self.assertEqual(len(self.client.get('/api/dashboard').json['rows']), 4)
        r = self.client.post('/api/chat', json={'question': 'בדיקה', 'conversation_id': 'test', 'school_id': '1001'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json['rows']), 1)
        self.assertEqual(r.json['advice_sources'], [])
        self.assertEqual(r.json['suggested_action']['status'], 'not_executed')
        self.assertEqual(self.client.get('/api/gaps').json['gaps'][0]['status'], 'open')
        self.assertEqual(self.client.patch('/api/gaps/1001', json={'status': 'resolved'}).status_code, 200)
        self.client.patch('/api/profile', json={'display_name': 'מפקחת'})
        restarted = create_app(self.config).test_client()
        self.assertEqual(restarted.get('/api/profile').json['profile']['display_name'], 'מפקחת')
        self.assertEqual(len(restarted.get('/api/conversations/test').json['messages']), 1)
        followup = restarted.post('/api/chat', json={'question': 'המשך', 'conversation_id': 'test'})
        self.assertEqual(followup.json['context']['school_id'], '1001')
        self.assertEqual(restarted.get('/api/gaps').json['gaps'][0]['status'], 'resolved')

    def test_import_validation_and_reporting(self):
        header = 'school_id,school,grade,previous,current,students\n'
        self.assertEqual(self.upload(header + '9999,x,ד,90,80,10').status_code, 403)
        for current in ('nan', 'inf', '-1', '101', 'bad'):
            self.assertEqual(self.upload(header + f'1001,x,ד,90,{current},10').status_code, 400)
        self.assertEqual(self.client.get('/api/dashboard').json['source'], 'demo_data')
        self.assertEqual(self.upload(header + '1001,בית ספר,ד,95,70,30').status_code, 200)
        self.assertEqual(self.client.get('/api/dashboard').json['summary']['average'], 70)
        result = self.client.post('/api/chat', json={'question': 'ניתוח'}).json
        self.assertEqual(result['source'], 'uploaded_csv')
        self.assertIn('70.0', self.client.get('/reports/attendance').text)
        self.assertEqual(self.client.delete('/api/files/attendance').status_code, 200)
        self.assertEqual(len(self.client.get('/api/dashboard').json['rows']), 4)

    def test_input_boundaries(self):
        for payload in ([], 'x', {'question': []}, {'question': 'x', 'conversation_id': '../bad'}):
            self.assertEqual(self.client.post('/api/chat', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/api/chat', json={'question': 'x', 'school_id': '9999'}).status_code, 403)
        self.assertEqual(self.client.patch('/api/profile', json={'permissions': ['9999']}).status_code, 400)
        self.assertEqual(self.client.patch('/api/profile', json={}, headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/files/attendance', data=b'x' * (1024 * 1024 + 1)).status_code, 413)

    def test_sources_and_scope(self):
        self.sources.write_text(json.dumps([{'id': 'a', 'title': 'Approved', 'approved': True, 'recommendation': 'Check attendance'}, {'id': 'b', 'title': 'Draft', 'approved': False, 'recommendation': 'Hidden'}]), encoding='utf-8')
        result = self.client.post('/api/chat', json={'question': 'המלצה'}).json
        self.assertEqual([s['id'] for s in result['advice_sources']], ['a'])
        self.assertNotIn('Hidden', result['answer'])
        agent = self.app.extensions['orchestrator']
        self.assertEqual(agent.rows('unauthorized-user'), [])
        self.assertEqual(self.app.extensions['local_store'].history('unauthorized-user', result['conversation_id']), [])


if __name__ == '__main__':
    unittest.main()
