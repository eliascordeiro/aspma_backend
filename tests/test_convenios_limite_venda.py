import pytest
import sys, pathlib

backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from modules.convenios.service import ConveniosService
from core.exceptions import ValidationError

class FakeRepoLimite:
    def __init__(self, socio_tipo=0, limite=1000.0, utilizado=0.0):
        self._socio = {
            'tipo': socio_tipo, 'limite': limite, 'sequencia': 5,
            'associado': 'JOAO TESTE', 'cpf': '12345678901'
        }
        self._utilizado = utilizado
        self.vendas = []
    # Métodos usados
    def fetch_socio_core(self, matricula):
        return self._socio if matricula == '123456' else None
    def soma_parcelas_mes(self, matricula, ano, mes):
        return self._utilizado
    def registrar_venda(self, venda: dict):
        self.vendas.append(venda)
    # Necessários para autenticar em outros testes (não usados aqui diretamente)
    def buscar_por_usuario_senha(self, *a, **k):
        return ('123','RAZAO','FANT','12345678000100','conv@test.com','X',0.0,12,'X')
    def listar_parcelas_mes(self, *a, **k): return []
    def listar_compras_mes(self, *a, **k): return []

class DummyMongo:
    pass

@pytest.fixture
def service_limite_suficiente():
    repo = FakeRepoLimite(limite=1200.0, utilizado=100.0)
    return ConveniosService(repo=repo, mongo_repo=DummyMongo())

@pytest.fixture
def service_limite_insuficiente():
    repo = FakeRepoLimite(limite=300.0, utilizado=50.0)  # saldo 250
    return ConveniosService(repo=repo, mongo_repo=DummyMongo())

@pytest.fixture
def service_venda():
    repo = FakeRepoLimite(limite=2000.0, utilizado=0.0)
    return ConveniosService(repo=repo, mongo_repo=DummyMongo())

@pytest.fixture
def service_venda_limite_apertado():
    # limite 500, utilizado 400 => disponível 100; venda tentativa com parcela > 100 deve falhar
    repo = FakeRepoLimite(limite=500.0, utilizado=400.0)
    return ConveniosService(repo=repo, mongo_repo=DummyMongo())

def test_calcular_limite_suficiente(service_limite_suficiente):
    resp = service_limite_suficiente.calcular_limite('123456', '1.200,00', 6)
    assert resp['insuficiente'] is False if 'insuficiente' in resp else True  # não deve marcar insuficiente
    assert resp['nr_parcelas'] == 6
    assert resp['associado'] == 'JOAO TESTE'

def test_calcular_limite_insuficiente(service_limite_insuficiente):
    # saldo disponível = 250; valor 3.001,00 / 12 => parcela ~250.08 > saldo => insuficiente
    resp = service_limite_insuficiente.calcular_limite('123456', '3.001,00', 12)
    assert resp.get('insuficiente') is True
    assert 'saldo' in resp

def test_registrar_venda_senha(service_venda):
    dados = {
        'matricula': '123456', 'associado': 'JOAO TESTE', 'sequencia': 6, 'nr_parcelas': 3,
        'valor': '900,00', 'mes': 5, 'ano': 2025, 'tipo': 0
    }
    ok = service_venda.registrar_venda_senha(dados, codigo_convenio='123', nome_convenio='RAZAO', usuario='userx')
    assert ok is True
    # Validar conversão numérica
    repo = service_venda.repo
    assert repo.vendas, 'Venda não registrada'
    venda = repo.vendas[0]
    assert venda['valor_parcela'] == '300.00'
    assert venda['nr_parcelas'] == 3
    assert venda['mes_final'] == 7  # 3 parcelas: meses 5,6,7


@pytest.mark.parametrize('dados_expected_error', [
    ({'matricula':'123456','associado':'A','sequencia':6,'nr_parcelas':0,'valor':'900,00','mes':5,'ano':2025,'tipo':0}, 'nr_parcelas'),
    ({'matricula':'123456','associado':'A','sequencia':6,'nr_parcelas':3,'valor':'0,00','mes':5,'ano':2025,'tipo':0}, 'valor'),
    ({'matricula':'123456','associado':'A','sequencia':6,'nr_parcelas':3,'valor':'900,00','mes':13,'ano':2025,'tipo':0}, 'mes'),
    ({'matricula':'123456','associado':'A','sequencia':6,'nr_parcelas':3,'valor':'900,00','mes':5,'ano':1999,'tipo':0}, 'ano'),
])
def test_registrar_venda_senha_validacoes(service_venda, dados_expected_error):
    dados, expected_fragment = dados_expected_error
    with pytest.raises(ValidationError) as exc:
        service_venda.registrar_venda_senha(dados, '123', 'RAZAO', 'userx')
    assert expected_fragment in str(exc.value)


def test_registrar_venda_senha_limite_revalidacao_falha(service_venda_limite_apertado):
    # valor 600, 3 parcelas => 200; disponível 100 => deve falhar
    dados = {
        'matricula': '123456', 'associado': 'JOAO TESTE', 'sequencia': 6, 'nr_parcelas': 3,
        'valor': '600,00', 'mes': 5, 'ano': 2025, 'tipo': 0
    }
    with pytest.raises(ValidationError) as exc:
        service_venda_limite_apertado.registrar_venda_senha(dados, '123', 'RAZAO', 'userx')
    assert 'limite' in str(exc.value)

def test_registrar_venda_senha_limite_revalidacao_ok(service_venda_limite_apertado):
    # valor 150, 3 parcelas => 50; disponível 100 => deve passar
    dados = {
        'matricula': '123456', 'associado': 'JOAO TESTE', 'sequencia': 6, 'nr_parcelas': 3,
        'valor': '150,00', 'mes': 5, 'ano': 2025, 'tipo': 0
    }
    ok = service_venda_limite_apertado.registrar_venda_senha(dados, '123', 'RAZAO', 'userx')
    assert ok is True


def test_registrar_venda_senha_normaliza_codigo_e_sequencia():
    """Garante que registrar_venda_senha normaliza codigo_convenio e sequencia.
    - codigo_convenio alfanumérico (ex.: 'FAKE123') deve persistir apenas dígitos ('123').
    - sequencia string (ex.: '07') deve ser convertida para inteiro (7).
    """
    repo = FakeRepoLimite(limite=1000.0, utilizado=0.0)
    service = ConveniosService(repo=repo, mongo_repo=DummyMongo())
    dados = {
        'matricula': '123456',
        'associado': 'JOAO TESTE',
        'sequencia': '07',  # string que deve virar int 7
        'nr_parcelas': 2,
        'valor': '100,00',
        'mes': 10,
        'ano': 2025,
        'tipo': 0
    }
    ok = service.registrar_venda_senha(dados, codigo_convenio='FAKE123', nome_convenio='RAZAO', usuario='dev')
    assert ok is True
    assert repo.vendas, 'Venda não registrada'
    venda = repo.vendas[0]
    assert venda['sequencia'] == 7
    assert venda['codigo_convenio'] == '123'
