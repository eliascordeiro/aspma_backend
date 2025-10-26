import pytest
from app_mvc import create_app
from flask_jwt_extended import decode_token

@pytest.mark.skip(reason="Requires configured MySQL & Mongo with convenios test data")
def test_convenio_password_flow(monkeypatch):
    app = create_app()
    client = app.test_client()

    # Mock mail sender to avoid real email
    sent = {}
    class DummyMail:
        def send(self, msg):
            sent['to'] = msg.recipients[0]
            # extract code from html
            import re
            m = re.search(r'(\d{6})', msg.html)
            if m:
                sent['codigo'] = m.group(1)
    from core import security
    security.mail = DummyMail()  # patch global mail instance

    # 1. Login (requires fixture data existing in DB) - illustrative only
    resp = client.post('/api/convenios/login', json={'usuario':'TESTE','senha':'123'})
    assert resp.status_code in (200,401)
    if resp.status_code != 200:
        return  # abort early if no fixture
    data = resp.get_json()['data']
    access = data['tokens']['access_token']

    # 2. Enviar código autenticado
    r2 = client.post('/api/convenios/enviar-codigo', json={'email': data['dados']['email']}, headers={'Authorization': f'Bearer {access}'})
    assert r2.status_code == 200
    assert 'codigo' in sent

    # 3. Alterar senha com código
    r3 = client.post('/api/convenios/alterar-senha-codigo', json={'codigo': sent['codigo'], 'nova_senha':'novaSenha#123'}, headers={'Authorization': f'Bearer {access}'})
    assert r3.status_code == 200

