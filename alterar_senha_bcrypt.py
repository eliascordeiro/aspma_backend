#!/usr/bin/env python3
"""
Script para alterar o campo senha da tabela convenio para suportar bcrypt (VARCHAR 255)
e manter compatibilidade com senhas antigas (plain text) e novas (bcrypt)
"""

import pymysql

print('🔧 Alterando tabela convenio para suportar bcrypt...')
print('=' * 70)

conn = pymysql.connect(
    host='yamabiko.proxy.rlwy.net',
    port=55104,
    user='root',
    password='zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE',
    database='railway'
)
cursor = conn.cursor()

# Ver dados atuais
cursor.execute('SELECT COUNT(*) FROM convenio')
total = cursor.fetchone()[0]
print(f'📊 Total de registros na tabela convenio: {total}')

cursor.execute('SELECT usuario, senha, LENGTH(senha) as senha_len FROM convenio LIMIT 5')
users = cursor.fetchall()
print('\n👥 Primeiros usuários (ANTES da alteração):')
print('-' * 70)
for usuario, senha, senha_len in users:
    print(f'Usuario: {usuario:<20} | Senha: {senha:<10} | Len: {senha_len}')

# Desabilitar strict mode temporariamente
print('\n🔧 Desabilitando strict mode temporariamente...')
cursor.execute("SET SESSION sql_mode = ''")

# Alterar campo senha
print('🔧 Alterando campo senha de VARCHAR(6) para VARCHAR(255)...')
cursor.execute('ALTER TABLE convenio MODIFY COLUMN senha VARCHAR(255)')
conn.commit()
print('✅ Campo senha alterado com sucesso!')

# Verificar alteração
cursor.execute('DESCRIBE convenio')
columns = cursor.fetchall()
for col in columns:
    if col[0] == 'senha':
        print(f'\n✅ Nova estrutura do campo senha: {col[1]}')

# Confirmar dados preservados
cursor.execute('SELECT usuario, senha, LENGTH(senha) as senha_len FROM convenio LIMIT 5')
users = cursor.fetchall()
print('\n👥 Primeiros usuários (DEPOIS da alteração - dados preservados):')
print('-' * 70)
for usuario, senha, senha_len in users:
    senha_tipo = 'bcrypt' if senha and senha.startswith('$2') else 'plain'
    print(f'Usuario: {usuario:<20} | Senha len: {senha_len:<3} | Tipo: {senha_tipo}')

conn.close()

print('\n' + '=' * 70)
print('🎉 SUCESSO! Agora a tabela suporta tanto senhas antigas (plain) quanto bcrypt!')
print('\n📝 Próximo passo: Ajustar o código de autenticação para aceitar ambos os tipos')
