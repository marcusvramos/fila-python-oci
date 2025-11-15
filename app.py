from flask import Flask, render_template, request, jsonify
import oci
import json
import requests
from datetime import datetime

app = Flask(__name__)

# Configuração OCI
config = oci.config.from_file()
queue_client = oci.queue.QueueClient(config)

# Configurações da fila
queue_id = "ocid1.queue.oc1.sa-saopaulo-1.amaaaaaak6s5riqam3ccheibdo2op4ej5rp57m7w7kwre4ypzxc73rk36eca"
queue_endpoint = "https://cell-1.queue.messaging.sa-saopaulo-1.oci.oraclecloud.com"

# Configurar endpoint personalizado
queue_client.base_client.endpoint = queue_endpoint


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/publicar', methods=['POST'])
def publicar():
    """Publica uma mensagem na fila"""
    try:
        data = request.get_json()
        email = data.get('email')
        mensagem = data.get('mensagem')

        if not email or not mensagem:
            return jsonify({'error': 'Email e mensagem são obrigatórios'}), 400

        # Criar mensagem para a fila
        put_messages_details = oci.queue.models.PutMessagesDetails(
            messages=[
                oci.queue.models.PutMessagesDetailsEntry(
                    content=json.dumps({
                        'email': email,
                        'msg': mensagem
                    })
                )
            ]
        )

        # Enviar para a fila
        result = queue_client.put_messages(
            queue_id=queue_id,
            put_messages_details=put_messages_details
        )

        return jsonify({
            'message': 'Mensagem enviada para a fila com sucesso!',
            'id': result.data.messages[0].id
        }), 200

    except Exception as e:
        print(f"Erro ao publicar mensagem: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/publicar-canal', methods=['POST'])
def publicar_canal():
    """Publica uma mensagem na fila com canal específico"""
    try:
        data = request.get_json()
        email = data.get('email')
        mensagem = data.get('mensagem')
        canal = data.get('canal', 'canal1')

        if not email or not mensagem:
            return jsonify({'error': 'Email e mensagem são obrigatórios'}), 400

        # Criar mensagem com metadados de canal
        put_messages_details = oci.queue.models.PutMessagesDetails(
            messages=[
                oci.queue.models.PutMessagesDetailsEntry(
                    content=json.dumps({
                        'email': email,
                        'msg': mensagem
                    }),
                    metadata=oci.queue.models.MessageMetadata(
                        channel_id=canal
                    )
                )
            ]
        )

        # Enviar para a fila
        result = queue_client.put_messages(
            queue_id=queue_id,
            put_messages_details=put_messages_details
        )

        return jsonify({
            'message': f'Mensagem enviada para o canal {canal} com sucesso!',
            'id': result.data.messages[0].id
        }), 200

    except Exception as e:
        print(f"Erro ao publicar mensagem no canal: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def stats():
    """Retorna estatísticas da fila"""
    try:
        # Buscar informações da fila
        queue_admin_client = oci.queue.QueueAdminClient(config)
        queue_info = queue_admin_client.get_queue(queue_id=queue_id)

        return jsonify({
            'nome': queue_info.data.display_name,
            'estado': queue_info.data.lifecycle_state,
            'criado': str(queue_info.data.time_created),
            'regiao': 'sa-saopaulo-1'
        }), 200

    except Exception as e:
        print(f"Erro ao obter estatísticas: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=== Sistema de Fila OCI ===")
    print(f"Queue ID: {queue_id}")
    print(f"Endpoint: {queue_endpoint}")
    print("Servidor iniciado em http://localhost:5002")
    app.run(debug=True, host='0.0.0.0', port=5002)
