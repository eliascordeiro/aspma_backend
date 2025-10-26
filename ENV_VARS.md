# ====================================
# VARIÁVEIS DE AMBIENTE - BACKEND
# ====================================
# 
# Este arquivo documenta todas as variáveis de ambiente necessárias
# para o deploy em produção. Copie e configure no seu provedor cloud.
#
# ⚠️ NUNCA commite valores reais! Use este como template.
# ====================================

# ==================
# SEGURANÇA
# ==================
SECRET_KEY=sua-chave-secreta-muito-forte-aqui-min-32-chars
JWT_SECRET_KEY=sua-chave-jwt-secreta-diferente-da-anterior

# ==================
# EMAIL (SMTP)
# ==================
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-de-app
MAIL_USE_TLS=true
MAIL_USE_SSL=false

# ==================
# MYSQL
# ==================
MYSQL_HOST=seu-mysql-host.cloud
MYSQL_PORT=3306
MYSQL_USER=seu_usuario
MYSQL_PASSWORD=sua_senha_mysql
MYSQL_DATABASE=nome_do_banco

# ==================
# MONGODB
# ==================
MONGO_URI=mongodb://usuario:senha@host:27017/database

# ==================
# FLASK
# ==================
FLASK_ENV=production
FLASK_APP=app_mvc.py
LOG_LEVEL=INFO

# ==================
# RATE LIMITING (Opcional)
# ==================
# REDIS_URL=redis://usuario:senha@host:6379/0

# ==================
# CORS (Frontend URLs)
# ==================
# FRONTEND_URL=https://seu-frontend.com

# ==================
# HEROKU/RAILWAY/RENDER
# ==================
# PORT=5000  # Geralmente setado automaticamente pela plataforma

# ==================
# TIMEZONE
# ==================
TZ=America/Sao_Paulo

# ==================
# WORKERS (Gunicorn)
# ==================
WEB_CONCURRENCY=4  # Número de workers (2-4 * CPU cores)
