# 🚀 Deploy Rápido - Railway (Recomendado)

## ⚡ Setup em 15 Minutos

### Pré-requisitos
- ✅ Código no GitHub
- ✅ Conta no Railway (gratuita)

### Passo 1: Commit das mudanças
```bash
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315

git add .
git commit -m "Preparado para deploy: adicionado gunicorn e configurações"
git push
```

### Passo 2: Railway
1. Acesse https://railway.app
2. Clique **"Login"** → Login com GitHub
3. Clique **"New Project"**
4. Selecione **"Deploy from GitHub repo"**
5. Escolha seu repositório
6. Railway detecta automaticamente e faz deploy!

### Passo 3: Configurar Banco de Dados

#### MySQL
```
1. No dashboard → Click "New" → "Database" → "Add MySQL"
2. Railway cria automaticamente e injeta variáveis:
   - MYSQLHOST
   - MYSQLPORT
   - MYSQLUSER
   - MYSQLPASSWORD
   - MYSQLDATABASE
```

#### MongoDB
```
1. No dashboard → Click "New" → "Database" → "Add MongoDB"
2. Railway cria automaticamente:
   - MONGO_URL
```

### Passo 4: Variáveis de Ambiente
No Railway Dashboard → Seu serviço → "Variables":

```bash
# Copie e cole (ajustando valores):
SECRET_KEY=gere-uma-chave-forte-aqui-com-32-chars-ou-mais
JWT_SECRET_KEY=gere-outra-chave-diferente-da-anterior
FLASK_ENV=production
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-app-google
MAIL_USE_TLS=true
LOG_LEVEL=INFO
TZ=America/Sao_Paulo
```

### Passo 5: Verificar Deploy
```bash
# Railway gera URL automaticamente:
# https://seu-app-production-xxxx.up.railway.app

# Testar:
curl https://seu-app-production-xxxx.up.railway.app/health
```

### Passo 6: Ver Logs
```bash
# No Railway Dashboard → Seu serviço → "Deployments" → "View Logs"
```

---

## 🎯 Endpoints para Testar

### 1. Health Check
```bash
curl https://seu-app.up.railway.app/health
# Deve retornar: {"status": "healthy"}
```

### 2. API Docs (Swagger)
```bash
# Acesse no navegador:
https://seu-app.up.railway.app/apidocs
```

### 3. Login Test
```bash
curl -X POST https://seu-app.up.railway.app/api/convenios/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"teste","senha":"1234"}'
```

---

## 🐛 Troubleshooting

### Erro: "Application failed to respond"
```bash
# Ver logs no Railway Dashboard
# Verificar se PORT está correto
# Gunicorn usa: --bind 0.0.0.0:$PORT
```

### Erro: "Database connection failed"
```bash
# Verificar variáveis de ambiente no Railway
# MySQL: MYSQLHOST, MYSQLPORT, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE
# MongoDB: MONGO_URI ou MONGO_URL
```

### Erro: "Module not found"
```bash
# Verificar se requirements.txt está completo
# Railway roda: pip install -r requirements.txt
```

---

## 🔄 Atualizações Futuras

Após o primeiro deploy, qualquer `git push` faz deploy automático! 🎉

```bash
# 1. Fazer mudanças no código
# 2. Commit
git add .
git commit -m "Nova funcionalidade"
git push

# 3. Railway detecta e faz redeploy automático!
```

---

## 💰 Custos

### Free Tier Railway
- **$5 de crédito/mês**
- ~500-550 horas de uptime
- Suficiente para MVP/desenvolvimento

### Quando Upgrade?
- Tráfego > 10k requests/dia
- Precisa de 100% uptime
- Databases maiores

---

## 📞 Próximo Passo

**Vou criar os arquivos necessários para você. Depois é só:**

1. ✅ Fazer commit
2. ✅ Push para GitHub
3. ✅ Conectar no Railway
4. ✅ Deploy automático! 🚀

**Quer que eu crie os arquivos agora?**
