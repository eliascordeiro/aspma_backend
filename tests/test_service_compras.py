import pytest, os
from modules.socios.service import SociosService
from core.exceptions import ValidationError

class FakeRepoCompras:
    def list_compras_mes(self, matricula, mes, ano):
        from datetime import datetime
        return [
            (datetime(2025, mes, 3), 'CONV X', 4, 80.0, 10),
            (datetime(2025, mes, 15), 'CONV Y', 2, 50.0, 11)
        ]

@pytest.fixture
def service():
    os.environ['ENABLE_FAKE_LOGIN'] = 'false'
    return SociosService(socios_repo=FakeRepoCompras(), mongo_repo=None, token_provider=lambda x: {})

def test_compras_ok(service):
    res = service.listar_compras_mensais('1234', '09-2025')
    assert res['total']
    assert len(res['dados']) == 2


def test_compras_mes_ano_invalido(service):
    with pytest.raises(ValidationError):
        service.listar_compras_mensais('1234', '9-2025')
