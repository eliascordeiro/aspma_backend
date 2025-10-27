from dotenv import load_dotenv
from datetime import timedelta
import os

# Carregamento de variáveis de ambiente com precedência:
# 1) .env no diretório de trabalho (quando rodando via IDE/CLI)
# 2) backend/.env (não sobrescreve o que já veio do processo ou do CWD)
# 3) .env.local na raiz do repositório (override=True)
# 4) backend/.env.local (override=True)
load_dotenv()  # CWD
_CFG_DIR = os.path.dirname(__file__)
_BACKEND_DIR = os.path.abspath(os.path.join(_CFG_DIR, '.'))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, '..'))

_ENV_PATH = os.path.join(_BACKEND_DIR, '.env')
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH, override=False)

for _local in (
    os.path.join(_REPO_ROOT, '.env.local'),
    os.path.join(_BACKEND_DIR, '.env.local'),
):
    if os.path.exists(_local):
        load_dotenv(_local, override=True)

"""LEGACY CONFIG MODULE

Esta classe Config permanece apenas para compatibilidade com código antigo
que ainda possa importar `from config import Config`. A nova configuração
centralizada está em `config/settings.py` com a classe `Settings` e instância
`settings`.

Planeje remover este arquivo após migração completa das referências externas.
"""

class Config(object):
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'default-mail-server')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'default-mail-username')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'default-mail-password')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'false').lower() in ('1','true','yes')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() in ('1','true','yes')
    
    MONGO_URI = os.getenv('MONGO_URI')
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER')
    # Compat: aceita MYSQL_PASSWORD (novo) e MYSQL_PASSWD (antigo)
    MYSQL_PASSWD = os.getenv('MYSQL_PASSWORD') or os.getenv('MYSQL_PASSWD')
    # Compat: aceita MYSQL_DATABASE (novo) e MYSQL_DB (antigo)
    MYSQL_DB = os.getenv('MYSQL_DATABASE') or os.getenv('MYSQL_DB')