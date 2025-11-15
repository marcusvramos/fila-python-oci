#!/bin/bash
set -e

# Configurações
INSTANCE_IP="${INSTANCE_IP:-144.22.230.225}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/oci_instance}"
REMOTE_USER="opc"
APP_DIR="/home/opc/fila-python"

echo "================================================"
echo "  Deploy Flask Queue Application"
echo "================================================"
echo ""

# Verificar chave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "Erro: Chave SSH não encontrada em $SSH_KEY"
    exit 1
fi

echo "==> Conectando ao servidor $INSTANCE_IP..."

# Parar os serviços
echo "==> Parando serviços Flask Queue..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $REMOTE_USER@$INSTANCE_IP \
    "sudo systemctl stop flask-queue flask-queue-consumer || true"

# Copiar arquivos da aplicação
echo "==> Copiando arquivos da aplicação..."
cd "$(dirname "$0")/.."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -r \
    app.py consumer.py requirements.txt templates/ static/ \
    $REMOTE_USER@$INSTANCE_IP:$APP_DIR/

# Copiar configuração OCI se existir
if [ -d ".oci" ]; then
    echo "==> Copiando configuração OCI..."
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -r \
        .oci/ \
        $REMOTE_USER@$INSTANCE_IP:/home/opc/

    # Corrigir caminho da chave no config
    echo "==> Corrigindo caminho da chave OCI..."
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $REMOTE_USER@$INSTANCE_IP \
        "sed -i 's|/Users/marcusramos/.oci/oci_api_key.pem|/home/opc/.oci/oci_api_key.pem|g' /home/opc/.oci/config"
fi

# Reinstalar dependências se requirements.txt mudou
echo "==> Atualizando dependências Python..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $REMOTE_USER@$INSTANCE_IP << 'ENDSSH'
source /home/opc/venv/bin/activate
pip install --upgrade -r /home/opc/fila-python/requirements.txt
ENDSSH

# Reiniciar serviços
echo "==> Reiniciando serviços Flask Queue..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $REMOTE_USER@$INSTANCE_IP \
    "sudo systemctl start flask-queue flask-queue-consumer"

# Aguardar um momento para o serviço iniciar
sleep 2

# Verificar status
echo "==> Verificando status dos serviços..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $REMOTE_USER@$INSTANCE_IP \
    "echo '--- Flask Queue App ---' && sudo systemctl status flask-queue --no-pager | head -15 && echo '' && echo '--- Flask Queue Consumer ---' && sudo systemctl status flask-queue-consumer --no-pager | head -15" || true

echo ""
echo "================================================"
echo "  Deploy concluído com sucesso!"
echo "================================================"
echo ""
echo "Aplicação disponível em:"
echo "  https://queue.144.22.230.225.nip.io/"
echo ""
