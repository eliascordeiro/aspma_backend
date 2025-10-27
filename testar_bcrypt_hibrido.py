#!/usr/bin/env python3
"""
Script de teste para verificar sistema híbrido de senhas (plain text + bcrypt)
e demonstrar migração automática
"""

import pymysql
import requests
import json
from datetime import datetime

# Configurações Railway
MYSQL_CONFIG = {
    'host': 'yamabiko.proxy.rlwy.net',
    'port': 55104,
    'user': 'root',
    'password': 'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE',
    'database': 'railway'
}

API_URL = "https://web-production-3c55ca.up.railway.app/api/convenios/login"

def conectar_mysql():
    return pymysql.connect(**MYSQL_CONFIG)

def verificar_tipo_senha(usuario):
    """Verifica se senha é plain text ou bcrypt"""
    conn = conectar_mysql()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT usuario, senha, LENGTH(senha) as len FROM convenio WHERE TRIM(usuario)=%s',
        (usuario.upper(),)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    usuario_db, senha_db, senha_len = result
    tipo = 'bcrypt' if senha_db and senha_db.startswith('$2') else 'plain text'
    
    return {
        'usuario': usuario_db,
        'senha_len': senha_len,
        'tipo': tipo,
        'senha_prefix': senha_db[:10] if senha_db else None
    }

def testar_login(usuario, senha):
    """Testa login via API"""
    payload = {
        'usuario': usuario,
        'senha': senha
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        return {
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'data': response.json()
        }
    except Exception as e:
        return {
            'status_code': 0,
            'success': False,
            'error': str(e)
        }

def listar_usuarios_teste():
    """Lista alguns usuários para teste"""
    conn = conectar_mysql()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT usuario, senha, LENGTH(senha) as len FROM convenio LIMIT 10'
    )
    results = cursor.fetchall()
    conn.close()
    
    usuarios = []
    for usuario, senha, senha_len in results:
        tipo = 'bcrypt' if senha and senha.startswith('$2') else 'plain text'
        usuarios.append({
            'usuario': usuario,
            'senha': senha if tipo == 'plain text' else '[HASH]',
            'tipo': tipo,
            'len': senha_len
        })
    
    return usuarios

def main():
    print('=' * 70)
    print('🔐 TESTE DO SISTEMA HÍBRIDO DE SENHAS (Plain Text + Bcrypt)')
    print('=' * 70)
    
    # 1. Listar usuários disponíveis
    print('\n📋 Primeiros 10 usuários no banco:')
    print('-' * 70)
    usuarios = listar_usuarios_teste()
    for u in usuarios:
        print(f"Usuario: {u['usuario']:<20} | Tipo: {u['tipo']:<12} | Len: {u['len']:<3} | Senha: {u['senha']}")
    
    # 2. Testar com usuário SANTISTA (senha plain text conhecida: 3000)
    print('\n' + '=' * 70)
    print('🧪 TESTE 1: Login com senha plain text (SANTISTA/3000)')
    print('=' * 70)
    
    print('\n1️⃣ ANTES do login - verificando tipo de senha:')
    info_antes = verificar_tipo_senha('SANTISTA')
    if info_antes:
        print(f"   Usuario: {info_antes['usuario']}")
        print(f"   Tipo: {info_antes['tipo']}")
        print(f"   Tamanho: {info_antes['senha_len']} caracteres")
        print(f"   Prefixo: {info_antes['senha_prefix']}")
    else:
        print('   ❌ Usuário não encontrado')
        return
    
    print('\n2️⃣ Fazendo login via API...')
    resultado = testar_login('SANTISTA', '3000')
    
    if resultado['success']:
        print('   ✅ Login bem-sucedido!')
        print(f"   Token recebido: {resultado['data'].get('access_token', 'N/A')[:50]}...")
    else:
        print(f"   ❌ Login falhou!")
        print(f"   Status: {resultado['status_code']}")
        print(f"   Erro: {resultado.get('data', resultado.get('error'))}")
    
    print('\n3️⃣ DEPOIS do login - verificando se senha foi migrada:')
    import time
    time.sleep(1)  # Aguarda 1 segundo para garantir que migração foi processada
    
    info_depois = verificar_tipo_senha('SANTISTA')
    if info_depois:
        print(f"   Usuario: {info_depois['usuario']}")
        print(f"   Tipo: {info_depois['tipo']}")
        print(f"   Tamanho: {info_depois['senha_len']} caracteres")
        print(f"   Prefixo: {info_depois['senha_prefix']}")
        
        if info_antes['tipo'] == 'plain text' and info_depois['tipo'] == 'bcrypt':
            print('\n   🎉 MIGRAÇÃO AUTOMÁTICA FUNCIONOU!')
            print('   ✅ Senha convertida de plain text para bcrypt')
        elif info_depois['tipo'] == 'bcrypt':
            print('\n   ℹ️ Senha já estava em bcrypt (login subsequente)')
        else:
            print('\n   ⚠️ Senha ainda está em plain text (verificar logs)')
    
    # 3. Estatísticas gerais
    print('\n' + '=' * 70)
    print('📊 ESTATÍSTICAS DO BANCO')
    print('=' * 70)
    
    conn = conectar_mysql()
    cursor = conn.cursor()
    
    # Total de usuários
    cursor.execute('SELECT COUNT(*) FROM convenio')
    total = cursor.fetchone()[0]
    print(f'\nTotal de convênios: {total}')
    
    # Usuários com bcrypt
    cursor.execute("SELECT COUNT(*) FROM convenio WHERE senha LIKE '$2%'")
    bcrypt_count = cursor.fetchone()[0]
    print(f'Senhas em bcrypt: {bcrypt_count}')
    
    # Usuários com plain text
    plain_count = total - bcrypt_count
    print(f'Senhas em plain text: {plain_count}')
    
    # Percentual migrado
    percentual = (bcrypt_count / total * 100) if total > 0 else 0
    print(f'\n✅ Migração: {percentual:.1f}% completa')
    
    conn.close()
    
    print('\n' + '=' * 70)
    print('✅ TESTE CONCLUÍDO!')
    print('=' * 70)

if __name__ == '__main__':
    main()
