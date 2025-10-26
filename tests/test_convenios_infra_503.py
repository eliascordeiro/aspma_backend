import os
import pytest
from app_mvc import create_app

# Força modo real (mas vamos simular falha de infra)
os.environ['ENABLE_FAKE_LOGIN'] = 'false'

class FailingRepo:
    def buscar_por_usuario(self, usuario):
        raise RuntimeError('db down')
    def buscar_por_usuario_senha(self, u, s):
        raise RuntimeError('db down')

class FailingMongo:
    def get_login_doc(self, usuario):
        raise RuntimeError('mongo down')

from modules.convenios.service import ConveniosService
from modules.convenios.service import Settings as ConvSettings

class DummySettings(ConvSettings):
    ENABLE_FAKE_LOGIN = False

@pytest.fixture
def app(monkeypatch):
    app = create_app()
    # Monkeypatch service global usado pelas rotas
    from modules.convenios import routes as conv_routes
    conv_routes.service = ConveniosService(repo=FailingRepo(), mongo_repo=FailingMongo(), settings=DummySettings())
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_infra_503(client):
    r = client.post('/api/convenios/login', json={'usuario': 'QUALQUER', 'senha': 'xxx'})
    assert r.status_code == 503, r.get_data(as_text=True)
    body = r.get_json()
    assert body['error']['code'] == 'BACKEND_UNAVAILABLE'
    assert 'temporariamente' in body['error']['message']
