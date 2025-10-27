# 🔧 Correção do Swagger - Como Fazer Deploy

## ✅ Correção Implementada Localmente

**Arquivo modificado:** `backend/app_mvc.py` (linha ~488)

### O que foi corrigido:

**ANTES:**
```python
@app.errorhandler(Exception)
def handle_generic(err: Exception):
    app.log_event('internal_error', error=str(err.__class__.__name__))
    app.logger.exception(err)
    return error_json(message='Erro interno', code='INTERNAL_ERROR', status_code=500)
```

**DEPOIS:**
```python
@app.errorhandler(Exception)
def handle_generic(err: Exception):
    # Não intercepta erros de rotas do Flasgger/Swagger
    from flask import request
    if request.path and (request.path.startswith('/api/docs') or 
                        request.path.startswith('/flasgger') or
                        request.path.startswith('/apispec')):
        # Deixa o Flasgger tratar seus próprios erros
        raise err
    
    app.log_event('internal_error', error=str(err.__class__.__name__))
    app.logger.exception(err)
    return error_json(message='Erro interno', code='INTERNAL_ERROR', status_code=500)
```

---

## 🚀 Como Fazer Deploy no Railway

### Opção 1: Via Railway CLI

```bash
# 1. Instalar Railway CLI (se ainda não tiver)
npm i -g @railway/cli

# 2. Fazer login
railway login

# 3. Link com o projeto
railway link

# 4. Deploy
railway up
```

### Opção 2: Via Git + Railway

```bash
# 1. Inicializar repositório (se necessário)
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315
git init
git add .
git commit -m "fix: Corrige Swagger apispec.json"

# 2. Adicionar remote do Railway
git remote add railway <SEU_RAILWAY_GIT_URL>

# 3. Push
git push railway main
```

### Opção 3: Via GitHub + Railway Auto-Deploy

```bash
# 1. Criar repositório no GitHub
# 2. Adicionar remote
git remote add origin <SEU_GITHUB_URL>
git push -u origin main

# 3. Conectar Railway ao GitHub (no dashboard Railway)
# Railway fará deploy automático a cada push
```

### Opção 4: Deploy Manual via Dashboard Railway

1. Acesse: https://railway.app/dashboard
2. Selecione seu projeto
3. Vá em "Settings" → "Deploy"
4. Clique em "Redeploy" ou faça upload manual do código

---

## 🧪 Como Testar Após Deploy

### 1. Verificar se apispec.json está acessível:

```bash
curl https://web-production-3c55ca.up.railway.app/api/docs/apispec.json
```

**Resultado esperado:**
```json
{
  "swagger": "2.0",
  "info": {
    "title": "ConsigExpress API",
    "version": "1.0"
  },
  "paths": {
    "/api/convenios/login": { ... },
    "/api/convenios/compras": { ... },
    ...
  }
}
```

### 2. Acessar Swagger UI no navegador:

```
https://web-production-3c55ca.up.railway.app/api/docs/
```

**Resultado esperado:**
- Interface Swagger carrega completamente
- Lista todas as rotas da API
- Permite testar endpoints interativamente

---

## 📊 Rotas que devem aparecer no Swagger:

### Convênios:
- `POST /api/convenios/login` - Login de convênio
- `POST /api/convenios/senha-codigo` - Gerar código para alterar senha
- `POST /api/convenios/senha-alterar` - Alterar senha com código
- `POST /api/convenios/senha-validar` - Validar senha atual
- `GET /api/convenios/compras/<mes>/<ano>` - Listar compras do mês
- `GET /api/convenios/parcelas/<mes>/<ano>` - Listar parcelas do mês
- `POST /api/convenios/vendas` - Registrar nova venda
- `GET /api/convenios/desconto` - Obter desconto do convênio
- `PUT /api/convenios/cadastro` - Atualizar cadastro

### Sócios:
- `POST /api/socios/login` - Login de sócio
- `POST /api/socios/senha-codigo` - Gerar código para alterar senha
- `POST /api/socios/senha-alterar` - Alterar senha com código
- `GET /api/socios/vendas` - Listar vendas do sócio
- `GET /api/socios/parcelas` - Listar parcelas do sócio

### System:
- `GET /` - Health check
- `GET /api/health` - Health detalhado (MySQL + MongoDB)

---

## ⚠️ Importante

**A correção já está aplicada localmente em:**
```
/media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315/backend/app_mvc.py
```

**Você só precisa fazer o deploy para o Railway!**

---

## 🔍 Verificar se Deploy Foi Bem-Sucedido

```bash
# Health check
curl https://web-production-3c55ca.up.railway.app/api/health

# Swagger spec
curl https://web-production-3c55ca.up.railway.app/api/docs/apispec.json | jq .

# Logs do Railway (via CLI)
railway logs
```

---

## 📝 Notas

- **Correção é simples:** apenas 6 linhas adicionadas
- **Não quebra funcionalidade existente:** apenas permite Flasgger funcionar
- **Zero downtime:** Railway faz deploy gradual
- **Rollback fácil:** se algo der errado, Railway permite reverter

---

## 🎯 Resumo

1. ✅ Correção feita localmente
2. ⏳ Aguardando deploy no Railway
3. 🧪 Após deploy, testar Swagger UI
4. 🎉 Swagger funcionará 100%!

