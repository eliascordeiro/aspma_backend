import pytest
from app_mvc import create_app
from modules.convenios.service import ConveniosService

class RepoOK:
    def listar_compras_mes(self, codigo, mes, ano):
        return []
    def buscar_por_usuario(self, u): return None
    def buscar_por_usuario_senha(self, u,s):
        # retorna linha fake (codigo, razao, fantasia, cgc, email, libera, desconto, parcelas, libera2)
        return ('C001','Razao','Fantasia','00.000.000/0000-00','mail@x.com','',0.0,5,'S')

class MongoOK:
    def get_login_doc(self, c): return {'codigo': c, 'bloqueio':'NAO'}
    def incrementar_tentativas(self,*a,**k): return 0
    def reset_tentativas(self,*a,**k): return None

@pytest.fixture
def app(monkeypatch):
    app = create_app()
    from modules.convenios import routes as conv_routes
    conv_routes.service = ConveniosService(repo=RepoOK(), mongo_repo=MongoOK())
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def token(client):
    # login fake habilitado? forçamos via env + senha especial
    import os
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    r = client.post('/api/convenios/login', json={'usuario':'LOJA_X','senha':'__dev__'})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    return body['data']['tokens']['access_token']

def test_convenios_compras_vazio(client, token):
    r = client.post('/api/convenios/compras', json={'mes_ano':'10-2025'}, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body['success'] is True
    assert body['data']['dados'] == []
