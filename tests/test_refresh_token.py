import os
import pytest
from app_mvc import create_app

@pytest.fixture(scope='module')
def client():
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    app = create_app()
    return app.test_client()


def test_refresh_flow(client):
    # Login para obter refresh
    r = client.post('/api/socios/login-extrato', json={'matricula': 'AAA1', 'cpf': '123456'})
    assert r.status_code == 200
    tokens = r.get_json()['data']['tokens']
    refresh = tokens['refresh_token']
    # Usar refresh
    resp = client.post('/api/socios/refresh', headers={'Authorization': f'Bearer {refresh}'})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()['data']
    assert 'access_token' in data


def test_refresh_sem_token(client):
    r = client.post('/api/socios/refresh')
    assert r.status_code in (401, 422)
