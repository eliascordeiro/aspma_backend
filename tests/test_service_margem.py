import pytest
from modules.socios.service import SociosService
from core.exceptions import AuthenticationError

class FakeRepoTipo1:
    def get_socio_core(self, matricula):
        return ('1', 1000.0, '12345678901')
    def get_matricula_atual(self, matricula):
        return '9999'
    def get_sum_parcelas(self, *args, **kwargs):
        return 0.0

class FakeRepoTipoA:
    def get_socio_core(self, matricula):
        return ('A', 2000.0, '12345678901')
    def get_matricula_atual(self, matricula):
        return None
    def get_sum_parcelas(self, matricula, ano, mes):
        return 750.0

class FakeRepoNotFound:
    def get_socio_core(self, matricula):
        return None


def test_margem_tipo1_placeholder():
    service = SociosService(socios_repo=FakeRepoTipo1(), mongo_repo=None, token_provider=lambda x: {})
    result = service.calcular_margem('1234')
    assert result['margem'] is None
    assert result['matricula'] == '9999'


def test_margem_tipoA_calculo():
    service = SociosService(socios_repo=FakeRepoTipoA(), mongo_repo=None, token_provider=lambda x: {})
    result = service.calcular_margem('1234')
    assert result['margem'] == 1250.0  # 2000 - 750
    assert result['limite'] == 2000.0
    assert result['consumo'] == 750.0
    assert 'mes_ref' in result


def test_margem_socio_nao_encontrado():
    service = SociosService(socios_repo=FakeRepoNotFound(), mongo_repo=None, token_provider=lambda x: {})
    with pytest.raises(AuthenticationError):
        service.calcular_margem('0000')
