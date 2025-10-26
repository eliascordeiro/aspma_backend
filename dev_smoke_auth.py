import os
os.environ.setdefault('FLASK_ENV','development')
os.environ.setdefault('DISABLE_RATE_LIMIT','true')
os.environ.setdefault('ENABLE_FAKE_LOGIN','true')
os.environ.setdefault('DEV_ESQUECEU_CODE_FALLBACK','true')

from app_mvc import create_app

app = create_app()
client = app.test_client()

# 1) Login fake para obter tokens
resp = client.post('/api/convenios/login', json={'usuario':'USERA','senha':'__dev__'})
try:
    print('login_status', resp.status_code)
    j = resp.get_json(silent=True) or {}
    print('login_success', j.get('success'))
    access = j['data']['tokens']['access_token']
except Exception as e:
    print('login_error', str(e))
    raise SystemExit(1)

# 2) Autenticação de ação
resp2 = client.post('/api/convenios/autenticacao', json={'senha':'qualquer'}, headers={'Authorization': f'Bearer {access}'})
print('aut_status', resp2.status_code)
print('aut_json', resp2.get_json(silent=True))

# 3) Preflight OPTIONS (CORS) – simulação básica
resp3 = client.open('/api/convenios/autenticacao', method='OPTIONS', headers={
    'Origin':'http://127.0.0.1:3000',
    'Access-Control-Request-Method':'POST'
})
print('options_status', resp3.status_code)
print('options_allow_origin', resp3.headers.get('Access-Control-Allow-Origin'))

# 4) Esqueceu Senha - Enviar Código (não autenticado)
resp4 = client.post('/api/convenios/esqueceu/enviar-codigo', json={'email': 'elias157508@gmail.com'})
print('esqueceu_status', resp4.status_code)
print('esqueceu_json', resp4.get_json(silent=True))
