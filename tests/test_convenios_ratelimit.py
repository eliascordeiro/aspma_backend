import pytest, sys, pathlib
backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app_mvc import create_app

@pytest.fixture
def app():
    app = create_app()
    return app

@pytest.fixture
def client(app):
    return app.test_client()

EMAIL = 'rltest@example.com'

def _call(client):
    return client.post('/api/convenios/esqueceu/enviar-codigo', json={'email': EMAIL})

def test_rate_limit_esqueceu_enviar_codigo(client):
    r1 = _call(client)
    assert r1.status_code in (200,401,400,500)  # primeira tentativa (dependendo se email existe) mas não limitada
    r2 = _call(client)
    assert r2.status_code in (200,401,400,500)
    r3 = _call(client)
    # Terceira deve estourar a janela 2/10minute => 429
    assert r3.status_code == 429, f"Esperado 429, obtido {r3.status_code}"
    data = r3.get_json()
    assert data['error']['code'] == 'RATE_LIMIT'
