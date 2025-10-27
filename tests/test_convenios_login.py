import os
import pytest
from app_mvc import create_app

# Força modo fake em testes de integração (sem dependências reais)
os.environ['ENABLE_FAKE_LOGIN'] = 'true'

@pytest.fixture(scope='module')
def app():
    app = create_app()
    return app

@pytest.fixture
def client(app):
    # Reinstancia service global para evitar interferência de outros testes (ex: 503)
    from modules.convenios import routes as conv_routes
    from modules.convenios.service import ConveniosService
    conv_routes.service = ConveniosService()  # service limpo
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    return app.test_client()

def test_login_convenio_fake_basic(client):
    r = client.post('/api/convenios/login', json={'usuario': 'LOJADEV', 'senha': '__dev__'})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body['data']['tokens']['fake'] is True
    assert body['meta']['fake_login'] is True
    assert body['data']['dados']['codigo'] == 'FAKE123'


def test_login_convenio_fake_alternative_keys(client):
    # Usa chaves alternativas (login / password)
    r = client.post('/api/convenios/login', json={'login': 'OUTRA', 'password': '__dev__'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['data']['tokens']['fake'] is True


def test_login_convenio_fake_legacy_payload(client):
    r = client.post('/api/convenios/login', json={'dados': {'usuario': 'LEGACY', 'senha': '__dev__'}})
    assert r.status_code == 200
    body = r.get_json()
    assert body['data']['tokens']['fake'] is True


def test_login_convenio_validation_error(client):
    # Envia payload vazio -> dados invalidos
    r = client.post('/api/convenios/login', json={})
    assert r.status_code == 400
    body = r.get_json()
    assert body['error']['code'] == 'VALIDATION_ERROR'
