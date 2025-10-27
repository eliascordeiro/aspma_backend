#!/usr/bin/env python3
"""
Script para criar usuário de teste na coleção login_convenios do MongoDB Railway
"""

from pymongo import MongoClient
import bcrypt

# Conectar ao MongoDB Railway
client = MongoClient('mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252/consigexpress?authSource=admin')
db = client['consigexpress']

print('🔧 Criando usuário de teste para a API...')
print('=' * 60)

# Criar senha hash com bcrypt
senha_teste = b'teste123'
senha_hash = bcrypt.hashpw(senha_teste, bcrypt.gensalt())

# Inserir ou atualizar usuário de teste
resultado = db.login_convenios.update_one(
    {'usuario': 'teste_api'},
    {'$set': {
        'usuario': 'teste_api',
        'senha': senha_hash,
        'nome': 'Usuario de Teste API',
        'email': 'teste@api.com'
    }},
    upsert=True
)

if resultado.upserted_id:
    print('✅ Usuário teste_api CRIADO com sucesso!')
elif resultado.modified_count > 0:
    print('✅ Usuário teste_api ATUALIZADO com sucesso!')
else:
    print('ℹ️ Usuário teste_api já existe (sem alterações)')

print('\n📋 Credenciais de teste:')
print('   Usuario: teste_api')
print('   Senha: teste123')

print('\n🧪 Teste o login com:')
print('curl -X POST https://web-production-3c55ca.up.railway.app/api/convenios/login \\')
print('  -H "Content-Type: application/json" \\')
print('  -d \'{"usuario":"teste_api","senha":"teste123"}\'')

# Verificar se foi criado
doc = db.login_convenios.find_one({'usuario': 'teste_api'})
if doc:
    print(f'\n✅ Verificação: Usuário existe no banco!')
    print(f'   Nome: {doc.get("nome")}')
    print(f'   Email: {doc.get("email")}')
    print(f'   Senha hash length: {len(doc.get("senha", b""))} bytes')

client.close()
print('\n🎉 Pronto para testar!')
