import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env from current working directory first, then fallback to backend/.env
load_dotenv()
_CFG_DIR = os.path.dirname(__file__)
_BACKEND_DIR = os.path.abspath(os.path.join(_CFG_DIR, '..'))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, '..'))

# Load backend/.env (base), do not override values already provided by process env or CWD .env
_ENV_PATH = os.path.join(_BACKEND_DIR, '.env')
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH, override=False)

# Load local overrides if present (override=True)
for _local_env in (
    os.path.join(_REPO_ROOT, '.env.local'),
    os.path.join(_BACKEND_DIR, '.env.local'),
):
    if os.path.exists(_local_env):
        load_dotenv(_local_env, override=True)

class Settings:
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_HOURS', '24')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_DAYS', '30')))

    # Database - MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
    MYSQL_POOL_SIZE = int(os.getenv('MYSQL_POOL_SIZE', '10'))

    # Database - MongoDB
    MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGODB_URI')
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', os.getenv('MONGODB_DATABASE', 'consigexpress'))

    # Backwards compatibility aliases
    MONGODB_URI = MONGO_URI
    MONGODB_DATABASE = MONGO_DATABASE

    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    # Default sender used by Flask-Mail when not provided explicitly
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

    # CORS - Adiciona domínios permitidos (Vercel + localhost para dev)
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://consigaspma.vercel.app,http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173').split(',')

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '1000 per hour')

    # Security
    RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')

    # Application Settings
    CORTE_DIA = int(os.getenv('CORTE_DIA', '9'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_FAKE_LOGIN = os.getenv('ENABLE_FAKE_LOGIN', 'False').lower() in ('true','1','yes')
    # Token Blocklist (Redis opcional)
    TOKEN_BLOCKLIST_REDIS_URL = os.getenv('TOKEN_BLOCKLIST_REDIS_URL')
    # Segurança convênios
    MAX_TENTATIVAS_CONVENIO = int(os.getenv('MAX_TENTATIVAS_CONVENIO', '5'))
    # Feature flags para desligar rotas legacy de convênios
    LEGACY_CONVENIOS_ENABLED = os.getenv('LEGACY_CONVENIOS_ENABLED', 'true').lower() in ('1','true','yes')
    LEGACY_CONVENIOS_SOFT_DEPRECATION = os.getenv('LEGACY_CONVENIOS_SOFT_DEPRECATION', 'true').lower() in ('1','true','yes')

    # WhatsApp (WhatsGw) - envio opcional de mensagens
    WHATSAPP_ENABLED = os.getenv('WHATSAPP_ENABLED', 'false').lower() in ('1','true','yes')
    WHATS_GW_API_URL = os.getenv('WHATS_GW_API_URL', 'https://app.whatsgw.com.br/api/WhatsGw/Send')
    WHATS_GW_APIKEY = os.getenv('WHATS_GW_APIKEY')  # obrigatória para envio
    WHATS_GW_SENDER = os.getenv('WHATS_GW_SENDER')  # número do remetente em E.164 (ex.: 5541987654321)
    WHATS_DEFAULT_DDD = os.getenv('WHATS_DEFAULT_DDD', '41')
    # De-duplication TTL (segundos) para evitar envios repetidos em curto intervalo
    WHATSAPP_DEDUP_TTL_SECONDS = int(os.getenv('WHATSAPP_DEDUP_TTL_SECONDS', '180'))

    @property
    def mysql_connection_params(self):
        return {
            'host': self.MYSQL_HOST,
            'port': self.MYSQL_PORT,
            'user': self.MYSQL_USER,
            'password': self.MYSQL_PASSWORD,
            'database': self.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'autocommit': True
        }

    def dict(self):
        return {k: getattr(self, k) for k in dir(self) if k.isupper()}

settings = Settings()