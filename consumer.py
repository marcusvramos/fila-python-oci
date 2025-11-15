#!/usr/bin/env python3
"""
Consumer de mensagens OCI Queue
Processa mensagens continuamente e envia e-mails
"""

import oci
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuração OCI
config = oci.config.from_file()
queue_client = oci.queue.QueueClient(config)

# Configurações da fila
queue_id = "ocid1.queue.oc1.sa-saopaulo-1.amaaaaaak6s5riqam3ccheibdo2op4ej5rp57m7w7kwre4ypzxc73rk36eca"
queue_endpoint = "https://cell-1.queue.messaging.sa-saopaulo-1.oci.oraclecloud.com"

# Configurar endpoint personalizado
queue_client.base_client.endpoint = queue_endpoint

# Configurações de e-mail
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = ''
EMAIL_PASS = ''


def enviar_email(assunto, destinatario, corpo_html):
    """Envia um e-mail usando SMTP do Gmail"""
    try:
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario

        # Adicionar corpo HTML
        html_part = MIMEText(corpo_html, 'html')
        msg.attach(html_part)

        # Conectar e enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"✓ E-mail enviado para {destinatario}")
        return True

    except Exception as e:
        print(f"✗ Erro ao enviar e-mail: {e}")
        return False


def processar_mensagem(mensagem):
    """Processa uma mensagem individual"""
    try:
        # Parse do conteúdo JSON
        conteudo = json.loads(mensagem.content)
        email = conteudo.get('email')
        msg = conteudo.get('msg')
        receipt = mensagem.receipt

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processando mensagem...")
        print(f"  Para: {email}")
        print(f"  Mensagem: {msg[:50]}..." if len(msg) > 50 else f"  Mensagem: {msg}")

        # Enviar e-mail
        sucesso = enviar_email("Mensagem da Fila OCI", email, msg)

        if sucesso:
            # Remover da fila
            queue_client.delete_message(
                queue_id=queue_id,
                message_receipt=receipt
            )
            print(f"✓ Mensagem removida da fila")
            return True
        else:
            # Recolocar na fila (tornar visível novamente em 30 segundos)
            update_details = oci.queue.models.UpdateMessagesDetails(
                entries=[
                    oci.queue.models.UpdateMessagesDetailsEntry(
                        receipt=receipt,
                        visibility_in_seconds=30
                    )
                ]
            )
            queue_client.update_messages(
                queue_id=queue_id,
                update_messages_details=update_details
            )
            print(f"⚠ Mensagem recolocada na fila (30s)")
            return False

    except Exception as e:
        print(f"✗ Erro ao processar mensagem: {e}")
        return False


def consumir_fila():
    """Loop principal - consome mensagens continuamente"""
    print("="*60)
    print("🚀 CONSUMER DE FILA OCI - INICIADO")
    print("="*60)
    print(f"Queue ID: {queue_id}")
    print(f"Endpoint: {queue_endpoint}")
    print(f"Região: São Paulo")
    print(f"E-mail configurado: {EMAIL_USER}")
    print("="*60)
    print("\n⏳ Aguardando mensagens...\n")

    mensagens_processadas = 0

    while True:
        try:
            # Buscar mensagens (máximo 10 por vez)
            get_messages_response = queue_client.get_messages(
                queue_id=queue_id,
                limit=10,
                timeout_in_seconds=30  # Long polling
            )

            mensagens = get_messages_response.data.messages

            if mensagens:
                print(f"\n📬 {len(mensagens)} mensagem(ns) recebida(s)")

                for mensagem in mensagens:
                    if processar_mensagem(mensagem):
                        mensagens_processadas += 1
                        print(f"📊 Total processado: {mensagens_processadas}")

                print(f"\n⏳ Aguardando novas mensagens...\n")

            # Pequeno delay para não sobrecarregar
            time.sleep(2)

        except KeyboardInterrupt:
            print("\n\n⚠ Encerrando consumer...")
            print(f"📊 Total de mensagens processadas: {mensagens_processadas}")
            print("👋 Consumer finalizado!\n")
            break

        except Exception as e:
            print(f"\n✗ Erro no loop principal: {e}")
            print("⏳ Tentando novamente em 5 segundos...\n")
            time.sleep(5)


if __name__ == '__main__':
    consumir_fila()
