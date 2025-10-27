#!/usr/bin/env python3
"""
Script para forçar migração de uma senha específica para bcrypt
Útil para testar a funcionalidade sem depender do login
"""

import pymysql
import bcrypt

# Configurações Railway
MYSQL_CONFIG = {
    'host': 'yamabiko.proxy.rlwy.net',
    'port': 55104,
    'user': 'root',
    'password': 'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE',
    'database': 'railway'
}

def migrar_senha_usuario(usuario, senha_conhecida):
    """Migra manualmente a senha de um usuário para bcrypt"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    print(f'🔍 Buscando usuário: {usuario}')
    cursor.execute(
        'SELECT usuario, senha, LENGTH(senha) FROM convenio WHERE TRIM(usuario)=%s',
        (usuario.upper(),)
    )
    result = cursor.fetchone()
    
    if not result:
        print(f'❌ Usuário {usuario} não encontrado!')
        conn.close()
        return False
    
    usuario_db, senha_atual, senha_len = result
    tipo_atual = 'bcrypt' if senha_atual and senha_atual.startswith('$2') else 'plain text'
    
    print(f'\n📋 Dados atuais:')
    print(f'   Usuario: {usuario_db}')
    print(f'   Tipo senha: {tipo_atual}')
    print(f'   Tamanho: {senha_len} caracteres')
    
    if tipo_atual == 'bcrypt':
        print(f'\n✅ Senha já está em bcrypt!')
        conn.close()
        return True
    
    # Verifica se senha conhecida está correta
    if senha_atual.strip() != senha_conhecida.strip():
        print(f'\n❌ Senha fornecida não confere com a do banco!')
        print(f'   Esperado: {senha_atual}')
        print(f'   Fornecido: {senha_conhecida}')
        conn.close()
        return False
    
    print(f'\n🔧 Migrando senha para bcrypt...')
    
    # Gera hash bcrypt
    senha_hash = bcrypt.hashpw(senha_conhecida.encode('utf8'), bcrypt.gensalt())
    
    # Atualiza no banco
    cursor.execute(
        'UPDATE convenio SET senha=%s WHERE TRIM(usuario)=%s',
        (senha_hash.decode('utf8'), usuario.upper())
    )
    conn.commit()
    
    print(f'✅ Senha migrada com sucesso!')
    
    # Verifica resultado
    cursor.execute(
        'SELECT senha, LENGTH(senha) FROM convenio WHERE TRIM(usuario)=%s',
        (usuario.upper(),)
    )
    result = cursor.fetchone()
    nova_senha, novo_len = result
    novo_tipo = 'bcrypt' if nova_senha.startswith('$2') else 'plain text'
    
    print(f'\n📋 Dados após migração:')
    print(f'   Tipo senha: {novo_tipo}')
    print(f'   Tamanho: {novo_len} caracteres')
    print(f'   Prefixo: {nova_senha[:10]}...')
    
    # Testa validação
    if bcrypt.checkpw(senha_conhecida.encode('utf8'), nova_senha.encode('utf8')):
        print(f'\n✅ Validação bcrypt: OK!')
    else:
        print(f'\n❌ Validação bcrypt: FALHOU!')
    
    conn.close()
    return True

if __name__ == '__main__':
    print('=' * 70)
    print('🔐 MIGRAÇÃO MANUAL DE SENHA PARA BCRYPT')
    print('=' * 70)
    print()
    
    # Migrar usuário SANTISTA
    sucesso = migrar_senha_usuario('SANTISTA', '3000')
    
    if sucesso:
        print('\n' + '=' * 70)
        print('🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!')
        print('=' * 70)
        print('\n🧪 Teste o login agora:')
        print('curl -X POST "https://web-production-3c55ca.up.railway.app/api/convenios/login" \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"usuario":"SANTISTA","senha":"3000"}\'')
    else:
        print('\n' + '=' * 70)
        print('❌ MIGRAÇÃO FALHOU')
        print('=' * 70)
