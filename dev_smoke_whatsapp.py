import os
os.environ.setdefault('FLASK_ENV','development')
os.environ.setdefault('DISABLE_RATE_LIMIT','true')
os.environ.setdefault('ENABLE_FAKE_LOGIN','true')

from app_mvc import create_app

app = create_app()
client = app.test_client()

# 1) Login fake para obter tokens
resp = client.post('/api/convenios/login', json={'usuario':'USERA','senha':'__dev__'})
j = resp.get_json(silent=True) or {}
access = j['data']['tokens']['access_token']

# 2) Calcular limite para matricula de teste
payload = {'matricula': '999999', 'valor': '600,00', 'nr_parcelas': 3}
resp2 = client.post('/api/convenios/limite', json=payload, headers={'Authorization': f'Bearer {access}'})
print('limite_status', resp2.status_code)
limite_json = resp2.get_json(silent=True) or {}
print('limite_json', limite_json)

# 3) Se limite OK e não insuficiente, registrar venda
msg = (limite_json.get('data') or limite_json.get('msg') or limite_json)
if isinstance(msg, dict) and not msg.get('insuficiente'):
    venda = {
        'matricula': msg.get('matricula','999999'),
        'valor': msg.get('valor_total','600,00'),
        'nr_parcelas': int(msg.get('nr_parcelas', 3)),
        'tipo': msg.get('tipo', 0),
        'sequencia': int((msg.get('sequencia') or 0)),
        'mes': int(msg.get('mes', 10)),
        'ano': int(msg.get('ano', 2025)),
        'saldo': float(str(msg.get('saldo','0')).replace('.','').replace(',','.')), 
        'cpf': msg.get('cpf') or None,
        'matricula_atual': msg.get('matricula') or None,
        'celular': msg.get('celular') or None,
        'associado': msg.get('associado') or 'JOAO TESTE'
    }
    resp3 = client.post('/api/convenios/venda-senha', json=venda, headers={'Authorization': f'Bearer {access}'})
    print('venda_status', resp3.status_code)
    print('venda_json', resp3.get_json(silent=True))
else:
    print('limite_insuficiente_ou_invalido')
