#!/usr/bin/env python3
"""
Script para verificar o status de todos os logins no MongoDB
"""

import sys
from pymongo import MongoClient
import os
import json


def get_mongo_connection():
    """Conecta ao MongoDB usando as variáveis de ambiente"""
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    mongo_db = os.getenv('MONGO_DB', 'aspmadb')
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        db = client[mongo_db]
        return db
    except Exception as e:
        print(f"❌ Erro ao conectar ao MongoDB: {e}")
        return None


def verificar_status():
    """Verifica status de todos os logins"""
    db = get_mongo_connection()
    if db is None:
        return False
    
    try:
        print("\n" + "="*70)
        print("   VERIFICAÇÃO DE STATUS - LOGIN CONVÊNIOS")
        print("="*70 + "\n")
        
        # Collection login_convenios
        login_convenios = db['login_convenios']
        todos_logins = list(login_convenios.find({}))
        
        if not todos_logins:
            print("ℹ️  Nenhum registro encontrado em 'login_convenios'\n")
        else:
            print(f"📋 Registros em 'login_convenios' ({len(todos_logins)}):")
            print("-" * 70)
            for doc in todos_logins:
                codigo = doc.get('codigo', 'N/A')
                bloqueio = doc.get('bloqueio', 'N/A')
                tentativas = doc.get('tentativas', 0)
                has_senha = 'senha' in doc
                print(f"Código: {codigo:<15} Bloqueio: {bloqueio:<5} Tentativas: {tentativas:<3} Senha: {'Sim' if has_senha else 'Não'}")
            print("-" * 70 + "\n")
        
        # Collection tentativas_convenio
        tentativas_coll = db['tentativas_convenio']
        todas_tentativas = list(tentativas_coll.find({}))
        
        if not todas_tentativas:
            print("ℹ️  Nenhum registro encontrado em 'tentativas_convenio'\n")
        else:
            print(f"📋 Registros em 'tentativas_convenio' ({len(todas_tentativas)}):")
            print("-" * 70)
            for doc in todas_tentativas:
                codigo = doc.get('codigo', 'N/A')
                tentativas = doc.get('tentativas', 0)
                print(f"Código: {codigo:<15} Tentativas: {tentativas}")
            print("-" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return False


def desbloquear_tudo():
    """Desbloqueia tudo e limpa tentativas"""
    db = get_mongo_connection()
    if db is None:
        return False
    
    try:
        print("\n" + "="*70)
        print("   LIMPEZA COMPLETA - DESBLOQUEIO TOTAL")
        print("="*70 + "\n")
        
        # Atualiza TODOS os registros em login_convenios
        login_convenios = db['login_convenios']
        result_update = login_convenios.update_many(
            {},
            {
                '$set': {'bloqueio': 'NAO'},
                '$unset': {'tentativas': ''}
            }
        )
        
        # Remove TODOS os registros de tentativas_convenio
        tentativas_coll = db['tentativas_convenio']
        result_delete = tentativas_coll.delete_many({})
        
        print(f"✅ Limpeza concluída!")
        print(f"   - Registros atualizados em login_convenios: {result_update.modified_count}")
        print(f"   - Registros removidos de tentativas_convenio: {result_delete.deleted_count}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao limpar: {e}")
        return False


if __name__ == '__main__':
    print("\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--limpar':
        desbloquear_tudo()
    else:
        verificar_status()
        print("\n💡 Para desbloquear tudo, execute:")
        print("   python3 verificar_status_login.py --limpar\n")
