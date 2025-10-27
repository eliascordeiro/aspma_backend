# 🔧 MIGRAÇÃO MANUAL - Comandos Copy/Paste

## 🚨 Problema Encontrado

O script anterior gerou um arquivo SQL com warnings do MySQL, causando erro na importação.

**Erro:**
```
ERROR 1064 (42000) at line 1: You have an error in your SQL syntax
```

**Causa:** Warnings do mysqldump foram incluídos no arquivo SQL.

---

## ✅ SOLUÇÃO: Migração Manual (Copy/Paste)

### Método 1: Script Corrigido (RECOMENDADO)

```bash
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315/backend
./migrate_quick.sh
```

Este script já está corrigido com:
- `2>/dev/null` para filtrar warnings
- `--skip-comments` para evitar comentários problemáticos
- `--set-gtid-purged=OFF` para compatibilidade

---

### Método 2: Comandos Manuais (Passo a Passo)

#### Passo 1: Limpar arquivo SQL corrompido (se existir)
```bash
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315/backend
rm -f aspma_backup_*.sql
```

#### Passo 2: Criar backup limpo
```bash
mysqldump \
  -h 200.98.112.240 \
  -u eliascordeiro \
  -p'D24m0733@!' \
  --single-transaction \
  --routines \
  --triggers \
  --skip-comments \
  --set-gtid-purged=OFF \
  aspma 2>/dev/null > backup_limpo.sql
```

**Verificar se criou OK:**
```bash
ls -lh backup_limpo.sql
head -20 backup_limpo.sql
```

Deve começar com algo como:
```sql
-- MySQL dump 10.13  Distrib 8.0.x
--
-- Host: 200.98.112.240    Database: aspma
-- ------------------------------------------------------

DROP TABLE IF EXISTS `tabela1`;
CREATE TABLE `tabela1` (
  ...
);
```

#### Passo 3: Importar para Railway
```bash
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway < backup_limpo.sql 2>/dev/null
```

#### Passo 4: Verificar importação
```bash
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway -e "SHOW TABLES; SELECT COUNT(*) as total FROM information_schema.tables WHERE table_schema='railway';" 2>/dev/null
```

---

### Método 3: Migração Direta (Pipe - Mais Rápido)

**⚠️ Cuidado:** Sem backup local, mas mais rápido.

```bash
mysqldump \
  -h 200.98.112.240 \
  -u eliascordeiro \
  -p'D24m0733@!' \
  --single-transaction \
  --routines \
  --triggers \
  --skip-comments \
  --set-gtid-purged=OFF \
  aspma 2>/dev/null | \
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway 2>/dev/null

echo "✅ Migração concluída!"
```

---

### Método 4: Apenas Estrutura (Sem Dados)

Se quiser testar primeiro só com a estrutura:

```bash
# Apenas estrutura (sem dados)
mysqldump \
  -h 200.98.112.240 \
  -u eliascordeiro \
  -p'D24m0733@!' \
  --no-data \
  --skip-comments \
  --set-gtid-purged=OFF \
  aspma 2>/dev/null | \
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway 2>/dev/null

echo "✅ Estrutura criada! Sem dados ainda."
```

---

## 🧪 TESTAR DEPOIS DA MIGRAÇÃO

### 1. Verificar tabelas
```bash
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway -e "SHOW TABLES;" 2>/dev/null
```

### 2. Contar registros
```bash
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway -e "
    SELECT table_name, table_rows 
    FROM information_schema.tables 
    WHERE table_schema='railway' 
    ORDER BY table_rows DESC;
  " 2>/dev/null
```

### 3. Testar query específica
```bash
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway -e "SELECT * FROM sua_tabela LIMIT 5;" 2>/dev/null
```

---

## 🔧 CONFIGURAR RAILWAY

Depois da migração bem-sucedida:

### Via Railway Dashboard (Web)
```
1. Acesse: https://railway.app/dashboard
2. Abra seu projeto
3. Click no serviço do backend
4. Tab "Variables"
5. Adicione:

MYSQL_HOST=yamabiko.proxy.rlwy.net
MYSQL_PORT=55104
MYSQL_USER=root
MYSQL_PASSWORD=zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE
MYSQL_DATABASE=railway
MYSQL_CHARSET=utf8mb4
```

### Outras variáveis necessárias:
```
MONGODB_URI=mongodb://araudata:d24m07.ana@consigexpress.mongodb.uhserver.com:27017/consigexpress
SECRET_KEY=sua_chave_secreta_flask_super_segura_aqui
JWT_SECRET_KEY=d24m07@!15750833
FLASK_ENV=production
LOG_LEVEL=INFO
TZ=America/Sao_Paulo
CORS_ORIGINS=https://seu-frontend.com
```

---

## 🧪 TESTAR BACKEND NO RAILWAY

### 1. Health Check
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

### 2. Testar Login
```bash
curl -X POST https://web-production-3c55ca.up.railway.app/api/convenios/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"teste","senha":"1234"}'
```

### 3. Ver Logs
```
Railway Dashboard → Deployments → View Logs
```

---

## 📊 TROUBLESHOOTING

### Erro: "Access denied"
```bash
# Verificar se a senha está correta
mysql -h yamabiko.proxy.rlwy.net -P 55104 -u root -p railway
# Digite a senha manualmente: zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE
```

### Erro: "Database 'railway' doesn't exist"
```bash
# Criar database (já deve existir, mas por garantia)
mysql -h yamabiko.proxy.rlwy.net -P 55104 -u root -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  -e "CREATE DATABASE IF NOT EXISTS railway CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
```

### Arquivo SQL corrompido
```bash
# Ver primeiras linhas do SQL
head -50 backup_limpo.sql

# Se tiver warnings ou texto estranho no início, refaça o backup com 2>/dev/null
```

### Importação muito lenta
```bash
# Desabilitar algumas checagens (mais rápido)
mysql \
  -h yamabiko.proxy.rlwy.net \
  -P 55104 \
  -u root \
  -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' \
  railway -e "
    SET FOREIGN_KEY_CHECKS=0;
    SET UNIQUE_CHECKS=0;
    SET AUTOCOMMIT=0;
  " 2>/dev/null

# Depois importar
mysql ... railway < backup_limpo.sql 2>/dev/null

# Reativar checagens
mysql ... railway -e "
    SET FOREIGN_KEY_CHECKS=1;
    SET UNIQUE_CHECKS=1;
    COMMIT;
  " 2>/dev/null
```

---

## ✅ RESUMO RÁPIDO

**Opção mais fácil:**
```bash
cd backend
./migrate_quick.sh
```

**Ou manualmente (3 comandos):**
```bash
# 1. Backup
mysqldump -h 200.98.112.240 -u eliascordeiro -p'D24m0733@!' --skip-comments --set-gtid-purged=OFF aspma 2>/dev/null > backup.sql

# 2. Importar
mysql -h yamabiko.proxy.rlwy.net -P 55104 -u root -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' railway < backup.sql 2>/dev/null

# 3. Verificar
mysql -h yamabiko.proxy.rlwy.net -P 55104 -u root -p'zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE' railway -e "SHOW TABLES" 2>/dev/null
```

**Pronto!** 🎉
