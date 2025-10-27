#!/usr/bin/env python3
"""
🚀 MIGRAÇÃO MONGODB → RAILWAY (Python)
======================================
Script Python para migrar dados do MongoDB externo para Railway
usando pymongo (mais confiável que mongorestore em alguns casos)
"""

from pymongo import MongoClient
from datetime import datetime
import sys

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*76}{Colors.NC}")
    print(f"{Colors.BLUE}{text:^76}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*76}{Colors.NC}\n")

def print_step(text):
    print(f"\n{Colors.BLUE}{'━'*76}{Colors.NC}")
    print(f"{Colors.YELLOW}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'━'*76}{Colors.NC}\n")

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# MongoDB Origem (Externo)
ORIGEM_URI = "mongodb://araudata:d24m07.ana@consigexpress.mongodb.uhserver.com:27017/consigexpress"
ORIGEM_DB = "consigexpress"

# MongoDB Destino (Railway)
DESTINO_URI = "mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252"
DESTINO_DB = "consigexpress"

# Collections a ignorar (sistema)
IGNORE_COLLECTIONS = ['system.indexes', 'system.profile', 'system.users']

print_header("🚀 MIGRAÇÃO MONGODB → RAILWAY")

print(f"{Colors.YELLOW}📋 Origem:{Colors.NC} {ORIGEM_DB} @ consigexpress.mongodb.uhserver.com")
print(f"{Colors.YELLOW}📋 Destino:{Colors.NC} {DESTINO_DB} @ shinkansen.proxy.rlwy.net")
print()

# ============================================================================
# PASSO 1: CONECTAR
# ============================================================================

print_step("🔗 PASSO 1: Conectando aos servidores...")

try:
    print(f"{Colors.YELLOW}Conectando à origem...{Colors.NC}")
    origem_client = MongoClient(ORIGEM_URI, serverSelectionTimeoutMS=5000)
    origem_client.admin.command('ping')
    origem_db = origem_client[ORIGEM_DB]
    print(f"{Colors.GREEN}✅ Origem conectada{Colors.NC}")
except Exception as e:
    print(f"{Colors.RED}❌ Erro na origem: {e}{Colors.NC}")
    sys.exit(1)

try:
    print(f"{Colors.YELLOW}Conectando ao destino...{Colors.NC}")
    destino_client = MongoClient(DESTINO_URI, serverSelectionTimeoutMS=5000)
    destino_client.admin.command('ping')
    destino_db = destino_client[DESTINO_DB]
    print(f"{Colors.GREEN}✅ Destino conectado{Colors.NC}")
except Exception as e:
    print(f"{Colors.RED}❌ Erro no destino: {e}{Colors.NC}")
    sys.exit(1)

# ============================================================================
# PASSO 2: LISTAR COLLECTIONS
# ============================================================================

print_step("📋 PASSO 2: Listando collections...")

origem_collections = [col for col in origem_db.list_collection_names() 
                      if col not in IGNORE_COLLECTIONS]

print(f"{Colors.GREEN}✅ {len(origem_collections)} collections encontradas:{Colors.NC}\n")

# Contar documentos na origem
collection_stats = {}
total_docs = 0

for col_name in sorted(origem_collections):
    count = origem_db[col_name].count_documents({})
    collection_stats[col_name] = count
    total_docs += count
    print(f"   ✓ {col_name}: {count:,} documentos")

print(f"\n{Colors.YELLOW}📊 Total: {total_docs:,} documentos a migrar{Colors.NC}")

# Confirmar migração
print(f"\n{Colors.YELLOW}⚠️  ATENÇÃO: Esta operação irá:{Colors.NC}")
print(f"   1. Dropar todas as collections existentes no destino")
print(f"   2. Copiar todos os dados da origem para o destino")
print()

resposta = input(f"{Colors.YELLOW}Deseja continuar? (s/N): {Colors.NC}").strip().lower()
if resposta != 's':
    print(f"{Colors.YELLOW}Migração cancelada pelo usuário.{Colors.NC}")
    sys.exit(0)

# ============================================================================
# PASSO 3: MIGRAR DADOS
# ============================================================================

print_step("📥 PASSO 3: Migrando dados...")

inicio = datetime.now()
migrados = 0
erros = []

for col_name in sorted(origem_collections):
    try:
        count = collection_stats[col_name]
        print(f"{Colors.YELLOW}Migrando {col_name} ({count:,} docs)...{Colors.NC}", end=' ')
        
        # Dropar collection no destino
        destino_db[col_name].drop()
        
        # Copiar documentos
        if count > 0:
            origem_col = origem_db[col_name]
            destino_col = destino_db[col_name]
            
            # Usar batch de 1000 documentos
            batch_size = 1000
            batch = []
            
            for doc in origem_col.find():
                batch.append(doc)
                
                if len(batch) >= batch_size:
                    destino_col.insert_many(batch, ordered=False)
                    batch = []
                    migrados += len(batch)
            
            # Inserir último batch
            if batch:
                destino_col.insert_many(batch, ordered=False)
                migrados += len(batch)
        
        print(f"{Colors.GREEN}✅{Colors.NC}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Erro: {str(e)[:50]}{Colors.NC}")
        erros.append((col_name, str(e)))

fim = datetime.now()
duracao = (fim - inicio).total_seconds()

# ============================================================================
# PASSO 4: VERIFICAR
# ============================================================================

print_step("🔍 PASSO 4: Verificando migração...")

print(f"{Colors.YELLOW}Comparando documentos...{Colors.NC}\n")

destino_collections = destino_db.list_collection_names()

total_origem_final = 0
total_destino_final = 0
diferencas = []

for col_name in sorted(origem_collections):
    origem_count = origem_db[col_name].count_documents({})
    destino_count = destino_db[col_name].count_documents({}) if col_name in destino_collections else 0
    
    total_origem_final += origem_count
    total_destino_final += destino_count
    
    if origem_count == destino_count:
        status = f"{Colors.GREEN}✅{Colors.NC}"
    else:
        status = f"{Colors.RED}⚠️{Colors.NC}"
        diferencas.append(col_name)
    
    print(f"{status} {col_name}: {origem_count:,} → {destino_count:,}")

# ============================================================================
# RESUMO
# ============================================================================

print_header("📊 RESUMO DA MIGRAÇÃO")

print(f"⏱️  Duração: {duracao:.2f} segundos")
print(f"📦 Collections: {len(origem_collections)}")
print(f"📄 Documentos origem: {total_origem_final:,}")
print(f"📄 Documentos destino: {total_destino_final:,}")

if erros:
    print(f"\n{Colors.RED}❌ Erros encontrados ({len(erros)}):{Colors.NC}")
    for col, erro in erros:
        print(f"   - {col}: {erro[:60]}")

if diferencas:
    print(f"\n{Colors.YELLOW}⚠️  Diferenças encontradas ({len(diferencas)}):{Colors.NC}")
    for col in diferencas:
        print(f"   - {col}")

if not erros and not diferencas:
    print(f"\n{Colors.GREEN}🎉 MIGRAÇÃO 100% CONSISTENTE!{Colors.NC}")
else:
    print(f"\n{Colors.YELLOW}⚠️  Migração concluída com avisos{Colors.NC}")

# Fechar conexões
origem_client.close()
destino_client.close()

print_header("✅ MIGRAÇÃO CONCLUÍDA")

print(f"{Colors.YELLOW}📝 Próximos passos:{Colors.NC}\n")
print("1. Configure no Railway Dashboard → Variables:")
print(f"   {Colors.BLUE}MONGODB_URI=mongodb://mongo:KyFRYfJSHAExpdLTAFQZWiRVenVCjwhx@shinkansen.proxy.rlwy.net:35252/consigexpress{Colors.NC}")
print()
print("2. Teste o backend:")
print(f"   {Colors.BLUE}curl https://web-production-3c55ca.up.railway.app/api/health{Colors.NC}")
print()
