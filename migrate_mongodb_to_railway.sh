#!/bin/bash

# ============================================================================
# 🚀 MIGRAÇÃO MONGODB → RAILWAY
# ============================================================================
# Script para migrar dados do MongoDB externo para o MongoDB do Railway
# 
# Origem: consigexpress.mongodb.uhserver.com:27017/consigexpress
# Destino: shinkansen.proxy.rlwy.net:35252/consigexpress
# ============================================================================

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}🚀 MIGRAÇÃO MONGODB → RAILWAY${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# MongoDB Origem (Externo)
ORIGEM_URI="mongodb://araudata:d24m07.ana@consigexpress.mongodb.uhserver.com:27017/consigexpress"
ORIGEM_DB="consigexpress"

# MongoDB Destino (Railway)
DESTINO_URI="mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252"
DESTINO_DB="consigexpress"

# Arquivo de backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./mongodb_backup_${TIMESTAMP}"

echo -e "${YELLOW}📋 Origem:${NC} ${ORIGEM_DB} @ consigexpress.mongodb.uhserver.com"
echo -e "${YELLOW}📋 Destino:${NC} ${DESTINO_DB} @ shinkansen.proxy.rlwy.net"
echo -e "${YELLOW}📋 Backup:${NC} ${BACKUP_DIR}"
echo ""

# ============================================================================
# PASSO 1: VERIFICAR CONEXÕES
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 PASSO 1: Verificando conexões...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Verificar mongodump
if ! command -v mongodump &> /dev/null; then
    echo -e "${RED}❌ mongodump não encontrado!${NC}"
    echo -e "${YELLOW}💡 Instale com: sudo apt install mongodb-database-tools${NC}"
    exit 1
fi

# Verificar mongorestore
if ! command -v mongorestore &> /dev/null; then
    echo -e "${RED}❌ mongorestore não encontrado!${NC}"
    echo -e "${YELLOW}💡 Instale com: sudo apt install mongodb-database-tools${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ferramentas MongoDB encontradas${NC}"

# Testar conexão origem
echo -e "${YELLOW}🔗 Testando MongoDB origem...${NC}"
python3 -c "
from pymongo import MongoClient
import sys
try:
    client = MongoClient('${ORIGEM_URI}', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client['${ORIGEM_DB}']
    collections = db.list_collection_names()
    print(f'✅ Origem OK! Collections: {len(collections)}')
    for col in collections:
        count = db[col].count_documents({})
        print(f'   ✓ {col}: {count:,} documentos')
    client.close()
except Exception as e:
    print(f'❌ Erro na origem: {e}')
    sys.exit(1)
" || exit 1

# Testar conexão destino
echo -e "${YELLOW}🔗 Testando MongoDB destino...${NC}"
python3 -c "
from pymongo import MongoClient
import sys
try:
    client = MongoClient('${DESTINO_URI}', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ Destino OK!')
    client.close()
except Exception as e:
    print(f'❌ Erro no destino: {e}')
    sys.exit(1)
" || exit 1

echo ""

# ============================================================================
# PASSO 2: CRIAR BACKUP
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}💾 PASSO 2: Criando backup do MongoDB origem...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

mongodump \
    --uri="${ORIGEM_URI}" \
    --db="${ORIGEM_DB}" \
    --out="${BACKUP_DIR}" \
    2>/dev/null

if [ $? -eq 0 ] && [ -d "${BACKUP_DIR}/${ORIGEM_DB}" ]; then
    BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
    echo -e "${GREEN}✅ Backup criado: ${BACKUP_SIZE}${NC}"
else
    echo -e "${RED}❌ Erro ao criar backup!${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASSO 3: RESTAURAR NO RAILWAY
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📥 PASSO 3: Restaurando no MongoDB Railway...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

mongorestore \
    --uri="${DESTINO_URI}" \
    --db="${DESTINO_DB}" \
    --drop \
    "${BACKUP_DIR}/${ORIGEM_DB}" \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Restauração concluída!${NC}"
else
    echo -e "${RED}❌ Erro na restauração!${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASSO 4: VERIFICAR MIGRAÇÃO
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 PASSO 4: Verificando migração...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

python3 -c "
from pymongo import MongoClient

# Conectar origem e destino
origem = MongoClient('${ORIGEM_URI}', serverSelectionTimeoutMS=5000)
destino = MongoClient('${DESTINO_URI}', serverSelectionTimeoutMS=5000)

origem_db = origem['${ORIGEM_DB}']
destino_db = destino['${DESTINO_DB}']

# Listar collections
origem_cols = set(origem_db.list_collection_names())
destino_cols = set(destino_db.list_collection_names())

print(f'✅ Collections migradas: {len(destino_cols)}')
print()
print('📊 Comparação de documentos:')

total_origem = 0
total_destino = 0

for col in sorted(origem_cols):
    origem_count = origem_db[col].count_documents({})
    destino_count = destino_db[col].count_documents({}) if col in destino_cols else 0
    total_origem += origem_count
    total_destino += destino_count
    
    status = '✅' if origem_count == destino_count else '⚠️'
    print(f'{status} {col}:')
    print(f'   Origem:  {origem_count:,} docs')
    print(f'   Destino: {destino_count:,} docs')

print()
print(f'📈 Total Origem:  {total_origem:,} documentos')
print(f'📈 Total Destino: {total_destino:,} documentos')

if total_origem == total_destino:
    print()
    print('🎉 Migração 100% consistente!')
else:
    print()
    print('⚠️  Diferenças detectadas!')

origem.close()
destino.close()
"

echo ""

# ============================================================================
# CONCLUSÃO
# ============================================================================

echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}🎉 MIGRAÇÃO MONGODB CONCLUÍDA!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo -e "${YELLOW}📝 Próximos passos:${NC}"
echo ""
echo -e "1. Configure no Railway Dashboard → Variables:"
echo -e "   ${BLUE}MONGODB_URI=mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252/consigexpress${NC}"
echo -e "   ${BLUE}MONGODB_DATABASE=consigexpress${NC}"
echo ""
echo -e "2. Teste o backend:"
echo -e "   ${BLUE}curl https://web-production-3c55ca.up.railway.app/api/health${NC}"
echo ""
echo -e "3. Backup salvo localmente em:"
echo -e "   ${BLUE}${BACKUP_DIR}${NC}"
echo ""
echo -e "${BLUE}============================================================================${NC}"
