#!/bin/bash

# ====================================================================
# 🔄 MIGRAÇÃO RÁPIDA E SEGURA - MYSQL PARA RAILWAY
# ====================================================================

set -e

echo "======================================================================"
echo "🚀 MIGRAÇÃO RÁPIDA: MySQL → Railway"
echo "======================================================================"
echo ""

# Configurações
ORIGEM_HOST="200.98.112.240"
ORIGEM_USER="eliascordeiro"
ORIGEM_PASS="D24m0733@!"
ORIGEM_DB="aspma"

DESTINO_HOST="yamabiko.proxy.rlwy.net"
DESTINO_PORT="55104"
DESTINO_USER="root"
DESTINO_PASS="zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE"
DESTINO_DB="railway"

BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

echo "📋 Origem: $ORIGEM_USER@$ORIGEM_HOST/$ORIGEM_DB"
echo "📋 Destino: $DESTINO_USER@$DESTINO_HOST:$DESTINO_PORT/$DESTINO_DB"
echo "📋 Backup: $BACKUP_FILE"
echo ""

# ====================================================================
# OPÇÃO 1: Backup + Importar (Seguro)
# ====================================================================

echo "💾 Criando backup..."
mysqldump \
    -h "$ORIGEM_HOST" \
    -u "$ORIGEM_USER" \
    -p"$ORIGEM_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --skip-comments \
    --set-gtid-purged=OFF \
    "$ORIGEM_DB" 2>/dev/null > "$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    echo "❌ Erro ao criar backup!"
    exit 1
fi

TAMANHO=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ Backup criado: $TAMANHO"
echo ""

echo "📥 Importando para Railway..."
mysql \
    -h "$DESTINO_HOST" \
    -P "$DESTINO_PORT" \
    -u "$DESTINO_USER" \
    -p"$DESTINO_PASS" \
    "$DESTINO_DB" < "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Importação concluída!"
else
    echo "❌ Erro na importação!"
    echo "Arquivo salvo em: $BACKUP_FILE"
    exit 1
fi

echo ""

# ====================================================================
# VERIFICAÇÃO
# ====================================================================

echo "🔍 Verificando migração..."

TABELAS=$(mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DESTINO_DB'" 2>/dev/null)

echo "✅ Tabelas no Railway: $TABELAS"
echo ""

echo "📊 Listando tabelas:"
mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" "$DESTINO_DB" -e "SHOW TABLES" 2>/dev/null | tail -n +2 | while read table; do
    COUNT=$(mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" "$DESTINO_DB" -N -e "SELECT COUNT(*) FROM $table" 2>/dev/null)
    echo "   ✓ $table ($COUNT registros)"
done

echo ""
echo "======================================================================"
echo "🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!"
echo "======================================================================"
echo ""
echo "📝 Próximos passos:"
echo ""
echo "1. Configure no Railway Dashboard → Variables:"
echo "   MYSQL_HOST=yamabiko.proxy.rlwy.net"
echo "   MYSQL_PORT=55104"
echo "   MYSQL_USER=root"
echo "   MYSQL_PASSWORD=zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE"
echo "   MYSQL_DATABASE=railway"
echo ""
echo "2. Teste o backend:"
echo "   curl https://web-production-3c55ca.up.railway.app/api/health"
echo ""
echo "3. Backup salvo localmente em:"
echo "   $BACKUP_FILE"
echo ""
echo "======================================================================"
