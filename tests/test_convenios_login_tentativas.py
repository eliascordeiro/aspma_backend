import pytest
import sys, pathlib

backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from modules.convenios.service import ConveniosService
from core.exceptions import AuthenticationError
from app_mvc import create_app

class FailingAuthMySQLRepo:
    def __init__(self):
        self.calls = 0
    def buscar_por_usuario_senha(self, usuario, senha):
        self.calls += 1
        return None  # sempre falha
    def buscar_por_usuario(self, usuario):
        # simula existencia de convênio para mapear código
        return ('999','RAZAO','FANT','12345678000100','conv@test.com','X',0.0,12,'X')
    # stubs
    def listar_parcelas_mes(self,*a,**k): return []
    def listar_compras_mes(self,*a,**k): return []
    def atualizar_senha_mysql(self,*a,**k): return True
    def fetch_socio_core(self,*a,**k): return None
    def soma_parcelas_mes(self,*a,**k): return 0.0
    def registrar_venda(self,*a,**k): return True

class AttemptMongoRepo:
    def __init__(self):
        self.login_docs = {'999': {'codigo': '999', 'email': 'conv@test.com', 'bloqueio': 'NAO'}}
        self.tentativas = {}
        self.bloqueados = set()
    def get_login_doc(self, codigo):
        return self.login_docs.get(codigo)
    def incrementar_tentativas(self, codigo):
        self.tentativas[codigo] = self.tentativas.get(codigo,0)+1
        return self.tentativas[codigo]
    def bloquear_login(self, codigo):
        self.bloqueados.add(codigo)
        self.login_docs[codigo]['bloqueio'] = 'SIM'
    def reset_tentativas(self, codigo):
        self.tentativas.pop(codigo, None)
    # stubs p/ interface
    def armazenar_codigo_email(self,*a,**k): pass
    def validar_codigo_email(self,*a,**k): return False
    def validar_codigo_global(self,*a,**k): return None
    def atualizar_senha_mongo(self,*a,**k): pass
    def remover_codigo(self,*a,**k): pass
    def buscar_por_email(self,*a,**k): return None

@pytest.fixture
def app_ctx():
    app = create_app()
    ctx = app.app_context(); ctx.push()
    yield app
    ctx.pop()

@pytest.fixture
def service():
    from config.settings import Settings
    s = Settings()
    s.MAX_TENTATIVAS_CONVENIO = 3  # reduzir para teste rápido
    return ConveniosService(repo=FailingAuthMySQLRepo(), mongo_repo=AttemptMongoRepo(), settings=s)


def test_tentativas_incremento_bloqueio(service, app_ctx):
    # 1a tentativa
    with pytest.raises(AuthenticationError) as e1:
        service.autenticar('userx','senha1')
    assert 'Tentativas restantes' in str(e1.value)
    # 2a
    with pytest.raises(AuthenticationError) as e2:
        service.autenticar('userx','senha2')
    assert 'Tentativas restantes' in str(e2.value)
    # 3a (atinge limite -> bloqueio)
    with pytest.raises(AuthenticationError) as e3:
        service.autenticar('userx','senha3')
    assert 'Usuário bloqueado' in str(e3.value)
    # nova tentativa após bloqueio
    with pytest.raises(AuthenticationError) as e4:
        service.autenticar('userx','senha4')
    assert 'Usuário bloqueado' in str(e4.value)
