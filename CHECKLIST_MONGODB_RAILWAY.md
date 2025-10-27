# ✅ CHECKLIST - VERIFICAR CONFIGURAÇÃO MONGODB

## 🔍 O QUE VERIFICAR NO RAILWAY DASHBOARD

### 1️⃣ Acesse as Variáveis
```
https://railway.app/dashboard
→ Seu projeto
→ Serviço backend
→ Aba "Variables"
```

### 2️⃣ Procure a variável `MONGODB_URI`

### 3️⃣ Verifique se o valor é EXATAMENTE:

```
mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252/consigexpress?authSource=admin
```

**ATENÇÃO aos detalhes:**
- ✅ Deve ter `?authSource=admin` no final
- ✅ Não pode ter espaços antes ou depois
- ✅ Deve estar na linha `MONGODB_URI` (não `MONGO_URI`)
- ✅ Deve terminar em `/consigexpress?authSource=admin`

### 4️⃣ Depois de Salvar

Railway deve mostrar:
- 🔄 "Redeploying..." ou similar
- ⏳ Aguarde até aparecer "✅ Deployed" ou "Active"
- ⏱️ Isso pode levar 30-60 segundos

### 5️⃣ Forçar Redeploy (se necessário)

Se salvou mas não reiniciou:
1. Clique nos 3 pontinhos (⋮) ao lado do serviço
2. Escolha "Redeploy"
3. Aguarde o deploy completar

---

## 🧪 TESTE MANUAL DA URI

Execute este comando para confirmar que a URI está correta:

```bash
python3 -c "
from pymongo import MongoClient
uri = 'mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252/consigexpress?authSource=admin'
client = MongoClient(uri, serverSelectionTimeoutMS=3000)
client.admin.command('ping')
print('✅ URI está correta!')
print(f'📦 Collections: {len(client.consigexpress.list_collection_names())}')
"
```

---

## 🚨 POSSÍVEIS PROBLEMAS

### Problema 1: Esqueceu de clicar em "Save" ou "Add"
**Solução:** Volte e salve a variável

### Problema 2: Railway não reiniciou
**Solução:** Force redeploy manualmente

### Problema 3: Variável com nome errado
**Solução:** Deve ser `MONGODB_URI` (não `MONGO_URI`)

### Problema 4: URI copiada errada
**Solução:** Copie do arquivo `MONGODB_URI_CORRETA.txt`

### Problema 5: Espaços extras na URI
**Solução:** Cole novamente sem espaços

---

## ✅ TESTE FINAL

Após salvar e Railway reiniciar, teste:

```bash
curl https://web-production-3c55ca.up.railway.app/api/health
```

**Deve retornar:**
```json
{
  "ok": true,
  "components": {
    "mysql": true,
    "mongo": true
  }
}
```

---

## 🆘 AINDA NÃO FUNCIONOU?

### Ver Logs do Railway

1. Railway Dashboard
2. Clique no serviço
3. Aba "Deployments"
4. Clique no deploy mais recente
5. "View Logs"

**Procure por:**
- ❌ `OperationFailure: Authentication failed`
- ❌ `MONGODB_URI` com valor antigo
- ✅ `Conexão MongoDB OK` (se aparecer, está funcionando!)

---

## 📞 PRECISA DE AJUDA?

Me envie:
1. Screenshot da variável `MONGODB_URI` no Railway
2. Logs do último deploy
3. Resultado do teste manual acima

Vou te ajudar a identificar o problema!
