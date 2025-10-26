import os
import pytest
from app_mvc import create_app

# Testa rota legacy /legacy/login_convenios_format_old
# que deve devolver formato antigo com tokens no topo

@pytest.fixture
def client():
    os.environ['ENABLE_FAKE_LOGIN'] = 'true'
    app = create_app()
    return app.test_client()


def test_legacy_old_format_fake_login(client):
    resp = client.post('/legacy/login_convenios_format_old', json={'usuario': 'LEGACYX', 'senha': '__dev__'})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    # Estrutura antiga: tokens no topo
    assert 'access_token' in body and body['access_token']
    assert 'refresh_token' in body and body['refresh_token']
    assert body.get('token_type') == 'Bearer'
    assert 'dados' in body and isinstance(body['dados'], dict)
    # Em fake login deve expor indicador
    assert body.get('fake_login') is True
    # Não deve conter wrapper 'success'
    assert 'success' not in body
    # Campos essenciais em dados
    for k in ('codigo', 'nome_razao', 'usuario'):
        assert k in body['dados']
