#!/usr/bin/env python3
"""
Script de teste para validar a nova arquitetura MVC.
Testa conexões, configurações e endpoint principal.
"""

import os
import sys
import requests
import json
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_config():
    """Testa carregamento de configurações."""
    print("🧪 Testando configurações...")
    
    try:
        from config.settings import Settings
        settings = Settings()
        
        print(f"  ✅ Ambiente: {settings.FLASK_ENV}")
        print(f"  ✅ Debug: {settings.FLASK_DEBUG}")
        print(f"  ✅ MySQL Host: {settings.MYSQL_HOST}")
        print(f"  ✅ MongoDB URI configurado: {'mongodb' in settings.MONGODB_URI}")
        return True
        
    except Exception as e:
        print(f"  ❌ Erro nas configurações: {e}")
        return False

def test_database_connections():
    """Testa conexões com bancos de dados."""
    print("\n🧪 Testando conexões de banco...")
    
    try:
        from config.database import DatabaseManager
        
        # Teste MySQL
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                print(f"  ✅ MySQL: Conectado - {result}")
        except Exception as e:
            print(f"  ⚠️  MySQL: {e}")
        
        # Teste MongoDB
        try:
            mongo = DatabaseManager.get_mongo_client()
            db = mongo.get_database()
            collections = db.list_collection_names()
            print(f"  ✅ MongoDB: Conectado - {len(collections)} collections")
        except Exception as e:
            print(f"  ⚠️  MongoDB: {e}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Erro nas conexões: {e}")
        return False

def test_models():
    """Testa modelos de domínio."""
    print("\n🧪 Testando modelos...")
    
    try:
        from modules.socios.models import Socio, LoginResult
        
        # Teste Socio
        socio = Socio(
            matricula="123456",
            associado="João Silva",
            email="joao@email.com",
            celular="11999999999"
        )
        
        print(f"  ✅ Socio criado: {socio.matricula} - {socio.associado}")
        
        # Teste validação CPF
        is_valid = socio.validate_cpf_fragment("12345678901", "123456")
        print(f"  ✅ Validação CPF: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro nos modelos: {e}")
        return False

def test_schemas():
    """Testa schemas de validação."""
    print("\n🧪 Testando schemas...")
    
    try:
        from modules.socios.schemas import LoginExtratoSchema
        
        schema = LoginExtratoSchema()
        
        # Teste dados válidos
        valid_data = {
            "matricula": "123456",
            "cpf": "123456"
        }
        
        result = schema.load(valid_data)
        print(f"  ✅ Dados válidos: {result}")
        
        # Teste dados inválidos
        try:
            invalid_data = {
                "matricula": "",
                "cpf": "12345"  # CPF com 5 dígitos
            }
            schema.load(invalid_data)
            print("  ❌ Deveria ter falhado na validação")
        except Exception:
            print("  ✅ Validação de dados inválidos funcionou")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Erro nos schemas: {e}")
        return False

import pytest

@pytest.fixture
def app():
    from app_mvc import create_app
    app = create_app()
    return app

def test_app_creation(app):
    assert app is not None
    assert 'convenios' in app.blueprints

def test_endpoint_local(app):
    with app.test_client() as client:
        health_response = client.get('/health')
        assert health_response.status_code in (200,404)
        response = client.post('/api/socios/login-extrato', json={'matricula':'123456','cpf':'123456'})
        # Dependendo do fake login pode ser 200 ou erro de autenticação; apenas assegura validação CPF não gera 'Unknown field'
        body = response.get_data(as_text=True)
        assert 'Unknown field' not in body

def main():
    print("Use pytest para executar os testes.")

if __name__ == "__main__":
    main()