#!/bin/bash

# ====================================================================
# 🔄 SCRIPT DE MIGRAÇÃO MYSQL
# De: Servidor Externo → Para: Railway MySQL
# ====================================================================

set -e  # Para em caso de erro

echo "======================================================================"
echo "🔄 MIGRAÇÃO DE DADOS: Servidor Externo → Railway MySQL"
echo "======================================================================"
echo ""

# ====================================================================
# CONFIGURAÇÕES
# ====================================================================

# Servidor ORIGEM (Externo)
ORIGEM_HOST="200.98.112.240"
ORIGEM_PORT="3306"
ORIGEM_USER="eliascordeiro"
ORIGEM_PASS="D24m0733@!"
ORIGEM_DB="aspma"

# Servidor DESTINO (Railway)
DESTINO_HOST="yamabiko.proxy.rlwy.net"
DESTINO_PORT="55104"
DESTINO_USER="root"
DESTINO_PASS="zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE"
DESTINO_DB="railway"

# Arquivo de backup
BACKUP_FILE="aspma_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "📋 Configurações:"
echo "   Origem: $ORIGEM_USER@$ORIGEM_HOST:$ORIGEM_PORT/$ORIGEM_DB"
echo "   Destino: $DESTINO_USER@$DESTINO_HOST:$DESTINO_PORT/$DESTINO_DB"
echo "   Backup: $BACKUP_FILE"
echo ""

# ====================================================================
# PASSO 1: VERIFICAR CONEXÕES
# ====================================================================

echo "🔍 PASSO 1: Verificando conexões..."
echo ""

echo "   Testando origem..."
if mysql -h "$ORIGEM_HOST" -P "$ORIGEM_PORT" -u "$ORIGEM_USER" -p"$ORIGEM_PASS" -e "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ Origem: OK"
else
    echo "   ❌ Origem: FALHOU"
    echo "   Não foi possível conectar ao servidor origem."
    exit 1
fi

echo "   Testando destino..."
if mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" -e "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ Destino: OK"
else
    echo "   ❌ Destino: FALHOU"
    echo "   Não foi possível conectar ao Railway MySQL."
    exit 1
fi

echo ""

# ====================================================================
# PASSO 2: LISTAR TABELAS
# ====================================================================

echo "📊 PASSO 2: Listando tabelas do banco origem..."
echo ""

TABELAS=$(mysql -h "$ORIGEM_HOST" -P "$ORIGEM_PORT" -u "$ORIGEM_USER" -p"$ORIGEM_PASS" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$ORIGEM_DB'")
echo "   Total de tabelas encontradas: $TABELAS"

# Listar nomes das tabelas
echo ""
echo "   Tabelas:"
mysql -h "$ORIGEM_HOST" -P "$ORIGEM_PORT" -u "$ORIGEM_USER" -p"$ORIGEM_PASS" -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='$ORIGEM_DB'" | while read table; do
    echo "   - $table"
done

echo ""

# ====================================================================
# PASSO 3: CALCULAR TAMANHO
# ====================================================================

echo "📏 PASSO 3: Calculando tamanho do banco..."
echo ""

TAMANHO=$(mysql -h "$ORIGEM_HOST" -P "$ORIGEM_PORT" -u "$ORIGEM_USER" -p"$ORIGEM_PASS" -N -e "
    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB'
    FROM information_schema.tables 
    WHERE table_schema = '$ORIGEM_DB';
")

echo "   Tamanho estimado: ${TAMANHO} MB"
echo ""

# Confirmar
read -p "📋 Deseja continuar com a migração? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "⏭️  Migração cancelada."
    exit 0
fi

# ====================================================================
# PASSO 4: EXPORTAR (DUMP)
# ====================================================================

echo ""
echo "💾 PASSO 4: Exportando banco de dados..."
echo "   Arquivo: $BACKUP_FILE"
echo ""

# Exportar filtrando warnings
mysqldump -h "$ORIGEM_HOST" -P "$ORIGEM_PORT" -u "$ORIGEM_USER" -p"$ORIGEM_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --add-drop-table \
    --skip-comments \
    "$ORIGEM_DB" 2>/dev/null > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "   ✅ Exportação concluída! Tamanho: $BACKUP_SIZE"
else
    echo "   ❌ Erro na exportação!"
    exit 1
fi

echo ""

# ====================================================================
# PASSO 5: IMPORTAR
# ====================================================================

echo "📥 PASSO 5: Importando para Railway MySQL..."
echo "   Isso pode levar alguns minutos dependendo do tamanho..."
echo ""

# Importar filtrando warnings
mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" "$DESTINO_DB" < "$BACKUP_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "   ✅ Importação concluída!"
else
    echo "   ❌ Erro na importação!"
    echo "   O arquivo de backup está salvo em: $BACKUP_FILE"
    echo ""
    echo "   Para debug, execute:"
    echo "   mysql -h $DESTINO_HOST -P $DESTINO_PORT -u $DESTINO_USER -p $DESTINO_DB < $BACKUP_FILE"
    exit 1
fi

echo ""

# ====================================================================
# PASSO 6: VERIFICAR
# ====================================================================

echo "🔍 PASSO 6: Verificando migração..."
echo ""

TABELAS_DESTINO=$(mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DESTINO_DB'")

echo "   Tabelas no destino: $TABELAS_DESTINO"

if [ "$TABELAS" -eq "$TABELAS_DESTINO" ]; then
    echo "   ✅ Número de tabelas: OK"
else
    echo "   ⚠️  Número de tabelas diferente!"
    echo "   Origem: $TABELAS | Destino: $TABELAS_DESTINO"
fi

echo ""

# Listar tabelas do destino
echo "   Tabelas no Railway:"
mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='$DESTINO_DB'" | while read table; do
    # Contar registros
    COUNT=$(mysql -h "$DESTINO_HOST" -P "$DESTINO_PORT" -u "$DESTINO_USER" -p"$DESTINO_PASS" -N -e "SELECT COUNT(*) FROM $DESTINO_DB.$table")
    echo "   - $table ($COUNT registros)"
done

echo ""

# ====================================================================
# RESUMO FINAL
# ====================================================================

echo "======================================================================"
echo "🎉 MIGRAÇÃO CONCLUÍDA!"
echo "======================================================================"
echo ""
echo "📊 Resumo:"
echo "   Origem: $ORIGEM_DB ($TABELAS tabelas)"
echo "   Destino: $DESTINO_DB ($TABELAS_DESTINO tabelas)"
echo "   Backup: $BACKUP_FILE ($BACKUP_SIZE)"
echo ""
echo "🔧 Próximos passos:"
echo ""
echo "1. Configurar variáveis no Railway Dashboard:"
echo "   MYSQL_HOST=yamabiko.proxy.rlwy.net"
echo "   MYSQL_PORT=55104"
echo "   MYSQL_USER=root"
echo "   MYSQL_PASSWORD=zAdbLSWDcOjkKGFZlobjXxuWwDIIMzuE"
echo "   MYSQL_DATABASE=railway"
echo ""
echo "2. Testar backend:"
echo "   curl https://web-production-3c55ca.up.railway.app/api/health"
echo ""
echo "3. Backup local salvo em:"
echo "   $BACKUP_FILE"
echo ""
echo "======================================================================"
