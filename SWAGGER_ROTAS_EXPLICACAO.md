# 📚 ROTAS SWAGGER - GUIA COMPLETO

## ✅ ROTA CORRETA DO SWAGGER

### 🎯 Interface Principal (Todas as APIs)
```
https://web-production-3c55ca.up.railway.app/api/docs/
```

Esta é a **ÚNICA** rota do Swagger UI.  
Ela mostra TODOS os endpoints: Convênios, Sócios, Health, etc.

---

## ❌ ROTAS QUE NÃO EXISTEM

Estas rotas **NÃO** funcionam:

```
❌ /api/docs/convenios     (não existe)
❌ /api/docs/socios        (não existe)  
❌ /apidocs                (não existe)
❌ /api/docs/apispec.json  (erro 500)
```

---

## 🎯 COMO USAR O SWAGGER

### Passo 1: Acesse a Interface
```
https://web-production-3c55ca.up.railway.app/api/docs/
```

### Passo 2: Navegue pelos Endpoints

O Swagger mostra TODOS os endpoints organizados por tag:

```
📁 Convenios
   POST   /api/convenios/login
   POST   /api/convenios/criar-venda
   GET    /api/convenios/vendas
   ...

📁 Socios
   POST   /api/socios/login
   GET    /api/socios/dados
   ...

📁 Health
   GET    /api/health
   GET    /health
   ...
```

### Passo 3: Filtre se Necessário

Na interface do Swagger, você pode:
- Clicar em uma tag para expandir/colapsar
- Usar o campo de busca (se disponível)
- Rolar até a seção desejada

---

## ⚠️ PROBLEMA CONHECIDO

**Status Atual:**  
O Swagger UI carrega, mas a especificação JSON (`/api/docs/apispec.json`) retorna erro 500.

**Causa:**  
Error handler global interceptando erros do Flasgger.

**Impacto:**  
- ⚠️ Swagger UI pode não carregar endpoints corretamente
- ✅ Todas as APIs funcionam normalmente via cURL/Postman
- ✅ Backend 100% operacional

**Solução:**  
Ver arquivo `FIX_SWAGGER_SPEC.md` para correção completa.

---

## 🚀 ALTERNATIVAS PARA DOCUMENTAÇÃO

### Opção 1: Usar cURL/Postman

**Endpoints Principais:**

```bash
# Login Convênios
POST /api/convenios/login
Body: {"usuario": "string", "senha": "string"}

# Criar Venda
POST /api/convenios/criar-venda
Headers: Authorization: Bearer <token>
Body: { ... }

# Listar Vendas
GET /api/convenios/vendas
Headers: Authorization: Bearer <token>

# Login Sócios
POST /api/socios/login
Body: {"usuario": "string", "senha": "string"}

# Health Check
GET /api/health
```

### Opção 2: Testar no Terminal

```bash
# Health Check
curl https://web-production-3c55ca.up.railway.app/api/health

# Login
curl -X POST https://web-production-3c55ca.up.railway.app/api/convenios/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"seu_usuario","senha":"sua_senha"}'

# Com Token JWT
TOKEN="seu_token_aqui"
curl -X GET https://web-production-3c55ca.up.railway.app/api/convenios/vendas \
  -H "Authorization: Bearer $TOKEN"
```

### Opção 3: Collection Postman

Crie uma collection com:

```
Base URL: https://web-production-3c55ca.up.railway.app

Endpoints:
├── Auth
│   ├── POST /api/convenios/login
│   └── POST /api/socios/login
├── Convênios
│   ├── GET /api/convenios/vendas
│   ├── POST /api/convenios/criar-venda
│   └── GET /api/convenios/limite-venda/:codigo
└── System
    ├── GET /health
    └── GET /api/health
```

---

## 🔍 ESTRUTURA DE ROTAS SWAGGER

### Como o Flasgger Funciona

O Flasgger:
1. Escaneia todas as rotas Flask
2. Lê as docstrings YAML
3. Gera uma especificação OpenAPI única
4. Exibe tudo em uma interface única

**NÃO há rotas separadas** por módulo como:
- ❌ `/api/docs/convenios`
- ❌ `/api/docs/socios`

**Há apenas UMA interface** que mostra tudo:
- ✅ `/api/docs/`

---

## 📝 ENDPOINTS DISPONÍVEIS

### Convênios

```
POST   /api/convenios/login
POST   /api/convenios/criar-venda
GET    /api/convenios/vendas
GET    /api/convenios/limite-venda/:codigo
POST   /api/convenios/validar-compra
GET    /api/convenios/compras/:usuario
```

### Sócios

```
POST   /api/socios/login
GET    /api/socios/dados
POST   /api/socios/atualizar
```

### Sistema

```
GET    /health
GET    /api/health
GET    /
```

---

## ✅ RESUMO

### O Que Usar:

```
✅ Interface Swagger (tentativa):
   https://web-production-3c55ca.up.railway.app/api/docs/

✅ APIs diretas (funcionam 100%):
   https://web-production-3c55ca.up.railway.app/api/...

✅ Postman/Insomnia (recomendado):
   Crie collection manualmente
```

### O Que NÃO Usar:

```
❌ /api/docs/convenios   (não existe)
❌ /api/docs/socios      (não existe)
❌ /apidocs              (não existe)
```

---

## 🎯 RECOMENDAÇÃO

**Para Desenvolvimento:**
Use Postman ou Insomnia - mais confiável e fácil de usar.

**Para Produção:**
O Swagger é opcional. As APIs funcionam perfeitamente sem ele.

**Para Testes:**
```bash
# Exemplo completo de teste
curl -X POST https://web-production-3c55ca.up.railway.app/api/convenios/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","senha":"senha123"}' \
  -v
```

---

## 📞 PRECISA DE AJUDA?

Se quiser testar um endpoint específico, me informe:
- Qual endpoint? (ex: login, criar-venda, etc)
- Que dados enviar?
- Espera qual resposta?

Posso gerar o comando cURL completo para você! 🚀

---

**💡 Dica:** O backend está 100% funcional. O problema é apenas com a interface visual do Swagger, não com as APIs em si!
