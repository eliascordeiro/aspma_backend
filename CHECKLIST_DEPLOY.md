# ✅ CHECKLIST DE DEPLOY

## 📦 Arquivos Criados/Modificados

### ✅ Essenciais para Deploy
- [x] `requirements.txt` - Adicionado `gunicorn==21.2.0`
- [x] `Procfile` - Otimizado com workers e threads
- [x] `app_mvc.py` - Adicionado endpoint `/health` na raiz
- [x] `railway.json` - Configuração específica Railway
- [x] `ENV_VARS.md` - Template de variáveis de ambiente
- [x] `.github/workflows/deploy.yml` - CI/CD automático

### 📚 Documentação
- [x] `DEPLOY_CLOUD.md` - Guia completo (todas as plataformas)
- [x] `DEPLOY_RAPIDO.md` - Guia rápido (15 minutos)

---

## 🚀 PRÓXIMOS PASSOS

### Opção 1: Deploy Rápido (RECOMENDADO)
```bash
# 1. Commit
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315
git add .
git commit -m "Preparado para deploy: gunicorn, health check, configs"
git push

# 2. Railway (15 minutos)
# - Acesse: https://railway.app
# - Login com GitHub
# - "New Project" → "Deploy from GitHub"
# - Adicione databases (MySQL + MongoDB)
# - Configure variáveis de ambiente
# - Deploy automático! 🎉
```

### Opção 2: Heroku (Tradicional)
```bash
# 1. Instalar Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# 2. Login
heroku login

# 3. Criar app
cd backend
heroku create seu-app-backend

# 4. Add databases
heroku addons:create cleardb:ignite  # MySQL
heroku addons:create mongolab:sandbox  # MongoDB

# 5. Configure env vars
heroku config:set SECRET_KEY="..."
heroku config:set JWT_SECRET_KEY="..."
# ... outras variáveis

# 6. Deploy
git push heroku main

# 7. Ver logs
heroku logs --tail
```

---

## 🔍 VERIFICAÇÕES PRÉ-DEPLOY

### ✅ Código
- [x] Gunicorn adicionado
- [x] Health check funcionando
- [x] CORS configurado
- [x] Rate limiting ativo
- [x] JWT configurado
- [x] Logging estruturado

### ✅ Configuração
- [x] Procfile otimizado
- [x] requirements.txt completo
- [x] runtime.txt (Python 3.8)
- [x] .env.example atualizado
- [x] WSGI entry point (wsgi_mvc.py)

### ⚠️ PENDENTE (Você precisa fazer)
- [ ] Criar repositório no GitHub (se não existe)
- [ ] Push do código
- [ ] Escolher plataforma (Railway/Heroku/Render)
- [ ] Configurar variáveis de ambiente
- [ ] Configurar databases
- [ ] Testar endpoints

---

## 🎯 ENDPOINTS PARA TESTAR APÓS DEPLOY

### 1. Health Check (Raiz)
```bash
curl https://seu-app.up.railway.app/
# Resposta:
{
  "status": "healthy",
  "service": "ConsigExpress Backend API",
  "version": "1.0.1",
  "docs": "/apidocs"
}
```

### 2. Health Check (Detalhado)
```bash
curl https://seu-app.up.railway.app/api/health
# Resposta:
{
  "ok": true,
  "components": {
    "mysql": true,
    "mongo": true
  },
  "details": {}
}
```

### 3. API Docs (Swagger)
```
Acesse no navegador:
https://seu-app.up.railway.app/apidocs
```

### 4. Login Test
```bash
curl -X POST https://seu-app.up.railway.app/api/convenios/login \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "teste",
    "senha": "1234"
  }'
```

---

## 🔐 VARIÁVEIS DE AMBIENTE OBRIGATÓRIAS

Copie esta lista para configurar no seu provedor:

```bash
# SEGURANÇA (GERE CHAVES FORTES!)
SECRET_KEY=xxxxx  # Min 32 caracteres
JWT_SECRET_KEY=xxxxx  # Min 32 caracteres

# MYSQL (Railway fornece automaticamente)
MYSQL_HOST=xxxxx
MYSQL_PORT=3306
MYSQL_USER=xxxxx
MYSQL_PASSWORD=xxxxx
MYSQL_DATABASE=xxxxx

# MONGODB (Railway fornece automaticamente)
MONGO_URI=mongodb://user:pass@host:port/db

# EMAIL
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-app
MAIL_USE_TLS=true

# CONFIGURAÇÃO
FLASK_ENV=production
LOG_LEVEL=INFO
TZ=America/Sao_Paulo
```

---

## 📊 PLATAFORMAS RECOMENDADAS

| Plataforma | Setup | Free Tier | Custo Hobby | Recomendação |
|------------|-------|-----------|-------------|--------------|
| **Railway** | ⭐⭐⭐⭐⭐ | $5/mês | $10-20 | ✅ **MELHOR** |
| **Heroku** | ⭐⭐⭐⭐ | 550h | $7/dyno | ✅ Confiável |
| **Render** | ⭐⭐⭐⭐ | 750h | $7 | ✅ Boa opção |
| **AWS** | ⭐⭐⭐ | 750h/12m | $30+ | Para escala |

---

## 💡 DICAS

### Gerar SECRET_KEY forte
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copie a saída e use como SECRET_KEY
```

### Gerar JWT_SECRET_KEY forte
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copie a saída e use como JWT_SECRET_KEY
```

### Testar localmente com Gunicorn
```bash
cd backend
pip install gunicorn
gunicorn 'app_mvc:create_app()' --bind 0.0.0.0:8000 --workers 2
# Acesse: http://localhost:8000
```

---

## 🐛 TROUBLESHOOTING

### Erro: "Address already in use"
```bash
# Ver processo usando porta
lsof -ti:5000
# Matar processo
kill -9 $(lsof -ti:5000)
```

### Erro: "No module named 'gunicorn'"
```bash
pip install gunicorn==21.2.0
```

### Erro: "Database connection failed"
```bash
# Verificar variáveis de ambiente
echo $MYSQL_HOST
echo $MONGO_URI
```

---

## 📞 SUPORTE

Se encontrar problemas:

1. **Verifique logs**:
   - Railway: Dashboard → Deployments → View Logs
   - Heroku: `heroku logs --tail`

2. **Teste localmente primeiro**:
   ```bash
   cd backend
   python3 app_mvc.py
   ```

3. **Verifique variáveis de ambiente**:
   - Todas as obrigatórias estão configuradas?
   - Valores estão corretos?

---

## ✅ PRONTO PARA DEPLOY!

**Tudo está configurado e pronto.** 

**Próximo passo**: 
1. Commit das mudanças
2. Push para GitHub
3. Conectar no Railway/Heroku
4. Deploy! 🚀

**Tempo estimado: 15-30 minutos**

---

## 📚 DOCUMENTAÇÃO

- **Completa**: `DEPLOY_CLOUD.md` (todas opções)
- **Rápida**: `DEPLOY_RAPIDO.md` (Railway)
- **Variáveis**: `ENV_VARS.md` (template)

**Boa sorte com o deploy! 🎉**
