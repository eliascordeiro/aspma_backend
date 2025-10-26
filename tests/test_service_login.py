import os
import pytest

# Garante que testes unitários deste módulo rodem fora do modo fake
os.environ['ENABLE_FAKE_LOGIN'] = 'false'
from app_mvc import create_app
from modules.socios.service import SociosService
from modules.socios.models import Socio, LoginResult
from core.exceptions import AuthenticationError

class FakeSociosRepo:
    def __init__(self, entries):
        self.entries = entries
    def find_by_matricula_cpf(self, matricula, cpf_fragment):
        data = self.entries.get(matricula)
        if not data:
            return None
        socio = Socio(
            matricula=matricula,
            associado=data['associado'],
            email=data.get('email'),
            celular=data.get('celular'),
            bloqueio=data.get('bloqueio'),
            tipo=data.get('tipo'),
            cpf=data.get('cpf')
        )
        # valida fragmento aqui de acordo com regra
        digits = ''.join(c for c in socio.cpf if c.isdigit())
        fragment_expected = digits[:3] + digits[-2:]
        if fragment_expected == cpf_fragment:
            return socio
        return None
    def get_bloqueio_aspma(self, matricula):
        return None

class FakeMongoRepo:
    def __init__(self, cache=None):
        self.cache = cache or {}
    def find_login_data(self, matricula):
        return self.cache.get(matricula)
    def store_login_data(self, socio):
        self.cache[socio.matricula] = {
            'matricula': socio.matricula,
            'associado': socio.associado,
            'email': socio.email,
            'celular': socio.celular,
            'bloqueio': socio.bloqueio,
            'tipo': socio.tipo,
            'cpf': socio.cpf
        }

class FakeSettings:
    ENABLE_FAKE_LOGIN = False
 
@pytest.fixture(scope='module')
def app():
    app = create_app()
    yield app

@pytest.fixture(autouse=True)
def _force_real_mode():
    # Garante que cada teste aqui não seja afetado por outros que habilitem fake
    os.environ['ENABLE_FAKE_LOGIN'] = 'false'

@pytest.fixture
def service(app):
    repo = FakeSociosRepo({
        '1001': {
            'associado': 'Maria Teste',
            'email': 'maria@example.com',
            'celular': '11999999999',
            'tipo': 'A',
            'cpf': '12345678901'
        }
    })
    mongo = FakeMongoRepo()
    svc = SociosService(socios_repo=repo, mongo_repo=mongo, settings=FakeSettings())
    return svc

def test_auth_success(app, service):
    with app.app_context():
        result = service.authenticate_extrato('1001', '12301')  # 123 + 01 (first3+last2)
        assert isinstance(result, LoginResult)
        assert result.socio.associado == 'Maria Teste'

def test_auth_fail_wrong_fragment(app, service):
    with app.app_context():
        with pytest.raises(AuthenticationError):
            service.authenticate_extrato('1001', '99999')

def test_auth_fail_unknown_matricula(app, service):
    with app.app_context():
        with pytest.raises(AuthenticationError):
            service.authenticate_extrato('9999', '12301')


@pytest.fixture
def client(app, monkeypatch):
    # força modo fake para fluxo integrado sem dependências externas
    monkeypatch.setenv('ENABLE_FAKE_LOGIN', 'true')
    return app.test_client()


def test_integration_login_margem_extrato(client):
    # Login
    r = client.post('/api/socios/login-extrato', json={'matricula': 'X1', 'cpf': '123456'})
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()['data']
    access = data['tokens']['access_token']
    headers = {'Authorization': f'Bearer {access}'}
    # Margem
    r2 = client.post('/api/socios/margem', headers=headers)
    assert r2.status_code == 200
    # Extrato (vazio no modo fake)
    r3 = client.post('/api/socios/extrato', json={'mes_ano': '09-2025'}, headers=headers)
    assert r3.status_code == 200
