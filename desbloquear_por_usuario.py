#!/usr/bin/env python3
"""
Script para desbloquear um convênio específico por USUÁRIO
Busca o código no MySQL e desbloqueia no MongoDB
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
import pymysql
from config.settings import Settings


def get_mongo_connection():
    """Conecta ao MongoDB"""
    settings = Settings()
    mongo_uri = settings.MONGO_URI
    mongo_db = settings.MONGO_DATABASE
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        db = client[mongo_db]
        return db
    except Exception as e:
        print(f"❌ Erro ao conectar ao MongoDB: {e}")
        return None


def get_mysql_connection():
    """Conecta ao MySQL"""
    settings = Settings()
    try:
        conn = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao MySQL: {e}")
        return None


def buscar_codigo_por_usuario(usuario):
    """Busca o código do convênio pelo usuário no MySQL"""
    conn = get_mysql_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            sql = "SELECT codigo FROM convenio WHERE usuario = %s"
            cursor.execute(sql, (usuario,))
            result = cursor.fetchone()
            return result['codigo'] if result else None
    except Exception as e:
        print(f"❌ Erro ao buscar usuário no MySQL: {e}")
        return None
    finally:
        conn.close()


def desbloquear_por_usuario(usuario):
    """Desbloqueia um convênio pelo nome de usuário"""
    print(f"\n🔍 Buscando código para usuário: {usuario}")
    
    # Busca o código no MySQL
    codigo = buscar_codigo_por_usuario(usuario)
    if not codigo:
        print(f"❌ Usuário '{usuario}' não encontrado no MySQL")
        return False
    
    print(f"✅ Código encontrado: {codigo}")
    
    # Desbloqueia no MongoDB
    db = get_mongo_connection()
    if db is None:
        return False
    
    try:
        # Remove bloqueio da collection login_convenios
        login_convenios = db['login_convenios']
        result_login = login_convenios.update_one(
            {'codigo': codigo},
            {
                '$set': {'bloqueio': 'NAO'},
                '$unset': {'tentativas': ''}
            }
        )
        
        # Remove registro de tentativas
        tentativas = db['tentativas_convenio']
        result_tentativas = tentativas.delete_one({'codigo': codigo})
        
        print(f"\n✅ Usuário '{usuario}' (código: {codigo}) desbloqueado com sucesso!")
        print(f"   - Login atualizado: {result_login.modified_count} registro(s)")
        print(f"   - Tentativas removidas: {result_tentativas.deleted_count} registro(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao desbloquear: {e}")
        return False


def desbloquear_tudo():
    """Desbloqueia todos os usuários"""
    db = get_mongo_connection()
    if db is None:
        return False
    
    try:
        # Atualiza todos os registros
        login_convenios = db['login_convenios']
        result_update = login_convenios.update_many(
            {},
            {
                '$set': {'bloqueio': 'NAO'},
                '$unset': {'tentativas': ''}
            }
        )
        
        # Remove todas as tentativas
        tentativas_coll = db['tentativas_convenio']
        result_delete = tentativas_coll.delete_many({})
        
        print(f"\n✅ Todos os convênios foram desbloqueados!")
        print(f"   - Logins atualizados: {result_update.modified_count} registro(s)")
        print(f"   - Tentativas removidas: {result_delete.deleted_count} registro(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao desbloquear: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("   DESBLOQUEAR CONVÊNIO POR USUÁRIO")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  python3 desbloquear_por_usuario.py <usuario>  - Desbloqueia um usuário específico")
        print("  python3 desbloquear_por_usuario.py --todos    - Desbloqueia todos os convênios")
        print()
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == '--todos':
        desbloquear_tudo()
    else:
        # Assume que é um nome de usuário
        desbloquear_por_usuario(comando)
    
    print()
