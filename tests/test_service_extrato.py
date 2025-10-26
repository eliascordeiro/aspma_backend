import pytest, os
from modules.socios.service import SociosService
from core.exceptions import ValidationError

class FakeRepoExtrato:
    def list_parcelas_mes(self, matricula, mes, ano):
        from datetime import datetime
        return [
            (1, 'CONVENIO A', datetime(2025, mes, 5), 3, 100.0, '1/3'),
            (2, 'CONVENIO B', datetime(2025, mes, 12), 2, 50.0, '1/2')
        ]

@pytest.fixture
def service():
    os.environ['ENABLE_FAKE_LOGIN'] = 'false'
    return SociosService(socios_repo=FakeRepoExtrato(), mongo_repo=None, token_provider=lambda x: {})

def test_extrato_ok(service):
    res = service.listar_descontos_mensais('1234', '09-2025')
    assert res['total']
    assert len(res['dados']) == 2


def test_extrato_mes_ano_invalido(service):
    with pytest.raises(ValidationError):
        service.listar_descontos_mensais('1234', '9-2025')
