import json
from app_mvc import create_app

def test_health_endpoint():
    app = create_app()
    client = app.test_client()
    r = client.get('/api/health')
    assert r.status_code in (200, 503)
    body = r.get_json()
    assert 'components' in body
    assert 'mysql' in body['components']
