from app.main import create_app

def test_health():
    app=create_app()
    with app.test_client() as client:
        r=client.get('/api/health')
        assert r.status_code==200 and r.json['status']=='ok'

def test_data():
    app=create_app()
    with app.test_client() as client:
        r=client.get('/api/dashboard')
        assert r.status_code==200 and len(r.json['rows'])==4

def test_chat():
    app=create_app()
    with app.test_client() as client:
        r=client.post('/api/chat',json={'question':'מה מצב הנוכחות?'})
        assert r.status_code==200 and r.json['suggested_action']['status']=='not_executed'
