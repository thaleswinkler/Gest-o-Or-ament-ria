#!/bin/bash
set -e

MSG="${1:-Atualização automática via AI Studio}"

echo "🔄 Sincronizando com o GitHub..."
git add -A
if git diff --staged --quiet; then
  echo "✅ Nenhuma alteração pendente para commit."
else
  git commit -m "$MSG"
  echo "📦 Alterações commitadas com a mensagem: '$MSG'"
fi

git push origin main
echo "🚀 Sincronizado com sucesso com https://github.com/thaleswinkler/Gest-o-Or-ament-ria.git!"
