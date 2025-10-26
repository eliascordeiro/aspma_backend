import os
import pytest
from app_mvc import create_app

@pytest.fixture(scope='module')
def app():
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    application = create_app()
    return application

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def access_token(client):
    resp = client.post('/api/socios/login-extrato', json={'matricula': 'ABC1', 'cpf': '123456'})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['data']['tokens']['access_token']


def test_codigo_compra_sucesso(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    payload = {
        'senha': 'qualquer',  # ignorada em fake mode
        'cpf': '123456',
        'email': 'integ@example.com',
        'celular': '11988887777'
    }
    r = client.post('/api/socios/codigo-compra', json=payload, headers=headers)
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()['data']
    assert data['codigo'] == 'FAKE1234'


def test_codigo_compra_cpf_invalido(client, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    payload = {
        'senha': 'x',
        'cpf': '12345',  # 5 digitos
        'email': 'a@b.com',
        'celular': '11999999999'
    }
    r = client.post('/api/socios/codigo-compra', json=payload, headers=headers)
    assert r.status_code == 400


def test_codigo_compra_sem_token(client):
    r = client.post('/api/socios/codigo-compra', json={})
    # Sem JWT deve retornar 401 (ou 422 dependendo do jwt-extended); aceitamos 401/422
    assert r.status_code in (401, 422)
