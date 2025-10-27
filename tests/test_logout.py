import os
import pytest
from app_mvc import create_app
from flask_jwt_extended import decode_token

@pytest.fixture(scope='module')
def client():
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    app = create_app()
    return app.test_client()


def _login(client):
    r = client.post('/api/socios/login-extrato', json={'matricula': 'LTT1', 'cpf': '123456'})
    assert r.status_code == 200
    tokens = r.get_json()['data']['tokens'] if 'tokens' in r.get_json()['data'] else {
        'access_token': r.get_json()['data']['access_token'],
        'refresh_token': r.get_json()['data']['refresh_token']
    }
    return tokens


def test_logout_revoga_access(client):
    tokens = _login(client)
    access = tokens['access_token']
    r = client.post('/api/socios/logout', headers={'Authorization': f'Bearer {access}'})
    assert r.status_code == 200
    # tentar reutilizar token revogado
    reuse = client.post('/api/socios/margem', headers={'Authorization': f'Bearer {access}'})
    assert reuse.status_code in (401, 422)


def test_logout_sem_token_ok(client):
    r = client.post('/api/socios/logout')
    # logout sem token apenas retorna sucesso vazio
    assert r.status_code == 200
