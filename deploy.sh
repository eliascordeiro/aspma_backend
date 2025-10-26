#!/bin/bash

# ====================================================================
# 🚀 SCRIPT DE DEPLOY AUTOMÁTICO - RAILWAY
# ====================================================================
# 
# Este script automatiza o processo de deploy do backend para Railway.
# Execute cada seção com atenção.
#
# ====================================================================

echo "🚀 Iniciando processo de deploy..."
echo ""

# ====================================================================
# PASSO 1: GERAR CHAVES DE SEGURANÇA
# ====================================================================
echo "🔐 Gerando chaves de segurança..."
echo ""
echo "SECRET_KEY:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
echo ""
echo "JWT_SECRET_KEY:"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
echo ""
echo "⚠️  COPIE E GUARDE ESSAS CHAVES! Você precisará delas no Railway."
echo ""
read -p "Pressione ENTER para continuar..."

# ====================================================================
# PASSO 2: VERIFICAR GIT
# ====================================================================
echo ""
echo "📦 Verificando repositório Git..."
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315

if [ ! -d ".git" ]; then
    echo "❌ Repositório Git não encontrado!"
    echo "Inicializando Git..."
    git init
    git add .
    git commit -m "Initial commit - Preparado para deploy"
    echo "✅ Git inicializado!"
else
    echo "✅ Git já inicializado!"
fi
echo ""

# ====================================================================
# PASSO 3: COMMIT DAS MUDANÇAS
# ====================================================================
echo "💾 Fazendo commit das mudanças de deploy..."
git add .
git status
echo ""
read -p "Fazer commit? (s/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    git commit -m "Deploy: Adicionado gunicorn, health check e configs cloud"
    echo "✅ Commit realizado!"
else
    echo "⏭️  Commit pulado."
fi
echo ""

# ====================================================================
# PASSO 4: CONFIGURAR REMOTE (GITHUB)
# ====================================================================
echo "🌐 Configurando GitHub..."
echo ""
echo "Você já tem um repositório no GitHub?"
echo "Se não, crie em: https://github.com/new"
echo ""
read -p "URL do repositório (ex: https://github.com/usuario/repo.git): " REPO_URL

if [ ! -z "$REPO_URL" ]; then
    # Remover remote antigo se existir
    git remote remove origin 2>/dev/null
    
    # Adicionar novo remote
    git remote add origin "$REPO_URL"
    echo "✅ Remote configurado: $REPO_URL"
    
    read -p "Fazer push para GitHub? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        git branch -M main
        git push -u origin main
        echo "✅ Push realizado!"
    else
        echo "⏭️  Push pulado. Execute manualmente: git push -u origin main"
    fi
else
    echo "⏭️  Remote não configurado."
fi
echo ""

# ====================================================================
# PASSO 5: INSTRUÇÕES RAILWAY
# ====================================================================
echo "======================================================================"
echo "🎉 PREPARAÇÃO COMPLETA!"
echo "======================================================================"
echo ""
echo "Agora siga estes passos no Railway:"
echo ""
echo "1. Acesse: https://railway.app"
echo "2. Login com GitHub"
echo "3. Click 'New Project' → 'Deploy from GitHub repo'"
echo "4. Selecione seu repositório"
echo "5. Railway faz deploy automático!"
echo ""
echo "6. Adicione Databases:"
echo "   - Click 'New' → 'Database' → 'Add MySQL'"
echo "   - Click 'New' → 'Database' → 'Add MongoDB'"
echo ""
echo "7. Configure variáveis de ambiente (Variables):"
echo "   SECRET_KEY=<copie a chave gerada acima>"
echo "   JWT_SECRET_KEY=<copie a outra chave gerada acima>"
echo "   FLASK_ENV=production"
echo "   MAIL_SERVER=smtp.gmail.com"
echo "   MAIL_PORT=587"
echo "   MAIL_USERNAME=seu-email@gmail.com"
echo "   MAIL_PASSWORD=sua-senha-app"
echo "   MAIL_USE_TLS=true"
echo "   LOG_LEVEL=INFO"
echo "   TZ=America/Sao_Paulo"
echo ""
echo "8. Railway conecta automaticamente MySQL e MongoDB!"
echo ""
echo "9. Acesse sua aplicação:"
echo "   https://seu-app-production-xxxx.up.railway.app"
echo ""
echo "======================================================================"
echo "📚 Documentação completa em:"
echo "   - backend/DEPLOY_CLOUD.md (todas opções)"
echo "   - backend/DEPLOY_RAPIDO.md (guia rápido)"
echo "   - backend/CHECKLIST_DEPLOY.md (checklist)"
echo "======================================================================"
echo ""
echo "✅ Tudo pronto para deploy! 🚀"
