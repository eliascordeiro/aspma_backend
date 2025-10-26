import pytest
import sys, pathlib

# Garante que o diretório backend esteja no PYTHONPATH quando o pytest é executado a partir de dentro dele.
backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from modules.convenios.service import ConveniosService
from core.exceptions import AuthenticationError
from flask_jwt_extended import decode_token
from app_mvc import create_app


class FakeMySQLRepo:
    """Simula operações MySQL necessárias aos testes (apenas autenticação e update de senha)."""
    def __init__(self):
        self.updated_passwords_mysql = []  # (codigo_convenio, senha_hash)
        # Mapas auxiliares para buscas simples
        self._email_by_codigo = {'123': 'conv@test.com'}
        self._codigo_by_email = {'conv@test.com': '123'}

    def buscar_por_usuario_senha(self, usuario, senha):
        return ('123','RAZAO','FANT','12345678000100','conv@test.com','X',0.0,12,'X')

    def buscar_por_usuario(self, usuario):
        return ('123','RAZAO','FANT','12345678000100','conv@test.com','X',0.0,12,'X')

    # Métodos não usados nestes testes mas esperados pela service
    def listar_parcelas_mes(self, *args, **kwargs):
        return []

    def listar_compras_mes(self, *args, **kwargs):
        return []

    def atualizar_senha_mysql(self, codigo_convenio, senha_hash):
        self.updated_passwords_mysql.append((codigo_convenio, senha_hash))

    # Placeholders para outras chamadas potenciais
    def fetch_socio_core(self, *args, **kwargs):
        return None

    def soma_parcelas_mes(self, *args, **kwargs):
        return 0.0

    def registrar_venda(self, *args, **kwargs):
        return True

    # --- Novos métodos usados pela service para validação de e-mail ---
    def buscar_email_por_codigo(self, codigo_convenio: str):
        return self._email_by_codigo.get(codigo_convenio)

    def buscar_codigo_por_email(self, email: str):
        return self._codigo_by_email.get(email)


class FakeMongoRepo:
    """Simula operações Mongo (códigos e atualização de senha)."""
    def __init__(self):
        self.login_docs = {'123': {'codigo': '123', 'email': 'conv@test.com'}}
        self.codes = {}            # codigo_convenio -> codigo
        self.global_codes = {}     # codigo -> codigo_convenio
        self.updated_passwords_mongo = []
        self.email_index = {'conv@test.com': {'codigo': '123', 'email': 'conv@test.com'}}
        self.validar_codigo_email_ok = True
        self.tentativas = {}
        self.bloqueados = set()

    def get_login_doc(self, codigo):
        return self.login_docs.get(codigo)

    def incrementar_tentativas(self, codigo):
        self.tentativas[codigo] = self.tentativas.get(codigo, 0) + 1
        return self.tentativas[codigo]

    def bloquear_login(self, codigo):
        self.bloqueados.add(codigo)
        # refletir no doc
        if codigo in self.login_docs:
            self.login_docs[codigo]['bloqueio'] = 'SIM'

    def reset_tentativas(self, codigo):
        self.tentativas.pop(codigo, None)

    def armazenar_codigo_email(self, codigo_convenio, codigo):
        self.codes[codigo_convenio] = codigo
        self.global_codes[codigo] = codigo_convenio

    def validar_codigo_email(self, codigo_convenio, codigo):
        return self.validar_codigo_email_ok and self.codes.get(codigo_convenio) == codigo

    def validar_codigo_global(self, codigo):
        if codigo in self.global_codes:
            return {'codigo_convenio': self.global_codes[codigo]}
        return None

    def atualizar_senha_mongo(self, codigo_convenio, senha_hash):
        self.updated_passwords_mongo.append((codigo_convenio, senha_hash))

    def remover_codigo(self, codigo_convenio):
        c = self.codes.pop(codigo_convenio, None)
        if c and c in self.global_codes:
            self.global_codes.pop(c)

    def buscar_por_email(self, email):
        return self.email_index.get(email.lower())

class FakeMailSender:
    def __init__(self):
        self.sent = []  # (email, codigo)
    def send_codigo(self, email, codigo):
        self.sent.append((email, codigo))

@pytest.fixture
def mysql_repo():
    return FakeMySQLRepo()

@pytest.fixture
def mongo_repo():
    return FakeMongoRepo()

@pytest.fixture
def mail_sender():
    return FakeMailSender()

@pytest.fixture
def service(mysql_repo, mongo_repo):
    return ConveniosService(repo=mysql_repo, mongo_repo=mongo_repo)

@pytest.fixture
def app_ctx():
    app = create_app()
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()

# --- Helpers -----------------------------------------------------------------------
@pytest.fixture
def fixed_code(monkeypatch):
    # força random.choices a devolver sempre '1','2','3','4','5','6'
    def fake_choices(sequence, k):
        return list('123456')
    import random
    monkeypatch.setattr(random, 'choices', fake_choices)
    return '123456'

# --- Tests -------------------------------------------------------------------------

def test_gerar_codigo_email_ok(service, mongo_repo, mail_sender, fixed_code):
    assert service.gerar_codigo_email('123', 'conv@test.com', mail_sender) is True
    assert mongo_repo.codes['123'] == fixed_code
    assert mail_sender.sent[0][1] == fixed_code


def test_gerar_codigo_email_email_invalido(service, mail_sender):
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_email('123', 'outro@test.com', mail_sender)


def test_alterar_senha_codigo_ok(service, mysql_repo, mongo_repo, mail_sender, fixed_code):
    # primeiro gerar
    service.gerar_codigo_email('123', 'conv@test.com', mail_sender)
    # alterar
    assert service.alterar_senha_codigo('123', fixed_code, 'NovaSenha#1') is True
    assert mysql_repo.updated_passwords_mysql, 'Senha não foi atualizada no MySQL'
    assert mongo_repo.updated_passwords_mongo, 'Senha não foi atualizada no Mongo'


def test_gerar_codigo_email_mysql_reverse_lookup_ok(service, mysql_repo, mongo_repo, mail_sender, fixed_code):
    # Desalinha Mongo para forçar fallback
    mongo_repo.login_docs['123']['email'] = 'diferente@no-mongo.com'
    # MySQL aponta que o e-mail pertence ao mesmo código
    mysql_repo._codigo_by_email['alias@test.com'] = '123'
    assert service.gerar_codigo_email('123', 'alias@test.com', mail_sender) is True


def test_gerar_codigo_email_mysql_reverse_lookup_fail(service, mysql_repo, mongo_repo, mail_sender):
    # E-mail mapeado para outro código no MySQL deve falhar
    mongo_repo.login_docs['123']['email'] = 'diferente@no-mongo.com'
    mysql_repo._codigo_by_email['outro@test.com'] = '999'  # diferente do código autenticado
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_email('123', 'outro@test.com', mail_sender)


def test_gerar_codigo_email_allow_dev_bypass(service, mysql_repo, mongo_repo, mail_sender, fixed_code):
    # Sem correspondência em Mongo nem MySQL, mas com bypass de dev ativado
    mongo_repo.login_docs['123']['email'] = 'nao-matcheia@mongo.com'
    mysql_repo._email_by_codigo['123'] = 'nao-matcheia@mysql.com'
    mysql_repo._codigo_by_email['dev@local'] = '999'  # propositalmente diferente
    assert service.gerar_codigo_email('123', 'dev@local', mail_sender, allow_dev_bypass=True) is True


def test_alterar_senha_codigo_invalido(service, mongo_repo):
    mongo_repo.validar_codigo_email_ok = False
    with pytest.raises(AuthenticationError):
        service.alterar_senha_codigo('123', '000000', 'NovaSenha#1')


def test_solicitar_codigo_esqueceu_ok(service, mongo_repo, mail_sender, fixed_code):
    assert service.solicitar_codigo_esqueceu('conv@test.com', mail_sender) is True
    # código global deve refletir
    assert fixed_code in mongo_repo.global_codes  # porque choices fixado


def test_alterar_senha_esqueceu_ok(service, mysql_repo, mongo_repo, mail_sender, fixed_code):
    service.solicitar_codigo_esqueceu('conv@test.com', mail_sender)
    code = list(mongo_repo.global_codes.keys())[0]
    assert service.alterar_senha_esqueceu(code, 'OutraSenha#2') is True
    assert mysql_repo.updated_passwords_mysql, 'Senha não foi atualizada (MySQL) no fluxo esqueceu'
    assert mongo_repo.updated_passwords_mongo, 'Senha não foi atualizada (Mongo) no fluxo esqueceu'


def test_alterar_senha_esqueceu_codigo_invalido(service):
    with pytest.raises(AuthenticationError):
        service.alterar_senha_esqueceu('999999', 'Senha#X')


def test_autenticar_identity_payload(service, app_ctx):
    """Garante que o access token contém identity estruturado (dict com codigo, nome_razao, usuario)."""
    conv, tokens = service.autenticar('USERA', 'SENHA')
    decoded = decode_token(tokens['access_token'])
    # Novo formato: sub = codigo (string), payload completo em claim custom 'identity'
    identity_claim = decoded.get('identity')
    assert isinstance(identity_claim, dict)
    assert identity_claim['codigo'] == conv.codigo
    assert identity_claim['nome_razao'] == conv.nome_razao
    assert identity_claim['usuario'] == conv.usuario
