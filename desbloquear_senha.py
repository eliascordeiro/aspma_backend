#!/usr/bin/env python3
"""
Script para desbloquear senha de convênio no MongoDB
Remove o bloqueio e reseta as tentativas de login
"""

import sys
import os

# Adiciona o diretório do backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import get_mongo_db


def desbloquear_convenio(codigo_convenio):
    """Desbloqueia um convênio no MongoDB"""
    try:
        db = get_mongo_db()
        if db is None:
            print("⚠️  Banco MongoDB não está disponível")
            return False
        
        # Remove bloqueio da collection login_convenios
        login_convenios = db['login_convenios']
        result_login = login_convenios.update_one(
            {'codigo': codigo_convenio},
            {
                '$set': {'bloqueio': 'NAO'},
                '$unset': {'tentativas': ''}
            }
        )
        
        # Remove registro de tentativas
        tentativas = db['tentativas_convenio']
        result_tentativas = tentativas.delete_one({'codigo': codigo_convenio})
        
        print(f"✅ Convênio '{codigo_convenio}' desbloqueado com sucesso!")
        print(f"   - Login atualizado: {result_login.modified_count} registro(s)")
        print(f"   - Tentativas removidas: {result_tentativas.deleted_count} registro(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao desbloquear convênio: {e}")
        return False


def desbloquear_todos():
    """Desbloqueia todos os convênios bloqueados"""
    try:
        db = get_mongo_db()
        if db is None:
            print("⚠️  Banco MongoDB não está disponível")
            return False
        
        # Remove todos os bloqueios
        login_convenios = db['login_convenios']
        result_login = login_convenios.update_many(
            {'bloqueio': 'SIM'},
            {
                '$set': {'bloqueio': 'NAO'},
                '$unset': {'tentativas': ''}
            }
        )
        
        # Remove todas as tentativas
        tentativas = db['tentativas_convenio']
        result_tentativas = tentativas.delete_many({})
        
        print(f"✅ Todos os convênios foram desbloqueados!")
        print(f"   - Logins atualizados: {result_login.modified_count} registro(s)")
        print(f"   - Tentativas removidas: {result_tentativas.deleted_count} registro(s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao desbloquear convênios: {e}")
        return False


def listar_bloqueados():
    """Lista todos os convênios bloqueados"""
    try:
        db = get_mongo_db()
        if db is None:
            print("⚠️  Banco MongoDB não está disponível")
            return False
        
        login_convenios = db['login_convenios']
        bloqueados = list(login_convenios.find({'bloqueio': 'SIM'}))
        
        if not bloqueados:
            print("ℹ️  Nenhum convênio bloqueado encontrado")
            return True
        
        print(f"\n📋 Convênios bloqueados ({len(bloqueados)}):")
        print("-" * 60)
        for doc in bloqueados:
            codigo = doc.get('codigo', 'N/A')
            tentativas = doc.get('tentativas', 0)
            print(f"   Código: {codigo:<20} Tentativas: {tentativas}")
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao listar bloqueados: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("   DESBLOQUEAR SENHA DE CONVÊNIO")
    print("="*60 + "\n")
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 desbloquear_senha.py <codigo_convenio>  - Desbloqueia um convênio específico")
        print("  python3 desbloquear_senha.py --todos            - Desbloqueia todos os convênios")
        print("  python3 desbloquear_senha.py --listar          - Lista convênios bloqueados")
        print()
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == '--todos':
        desbloquear_todos()
    elif comando == '--listar':
        listar_bloqueados()
    else:
        # Assume que é um código de convênio
        desbloquear_convenio(comando)
    
    print()
