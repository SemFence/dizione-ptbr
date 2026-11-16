#!/usr/bin/env bash
# Baixa o dicionário MFA pt-BR (CC BY 4.0) para data/sources/. Não vai para o git.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/sources
gh release download dictionary-portuguese_brazil_mfa-v2.0.0a -R MontrealCorpusTools/mfa-models -p '*.dict' -D data/sources --clobber
ls -l data/sources
