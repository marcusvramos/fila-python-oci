# DOCUMENTAÇÃO TÉCNICA – Sistema de Fila Python com OCI

Este documento explica em detalhes como o projeto funciona, arquivo por arquivo, para que você consiga entender o fluxo completo e explicar para outra pessoa (professor, banca, colega, etc.).

---

## 1. Visão Geral da Arquitetura

O sistema é composto por quatro grandes blocos:

- **Frontend (interface web)**  
  - Arquivos: `templates/index.html`, `static/css/style.css`, `static/js/app.js`  
  - Permite o usuário digitar um e-mail e uma mensagem, escolher se quer enviar para a fila normal ou para um canal específico, e visualizar informações da fila.

- **API Flask (app.py)**  
  - Arquivo: `app.py`  
  - Servidor web em Python usando Flask.  
  - Recebe requisições HTTP do frontend, publica mensagens na fila da OCI e fornece estatísticas da fila.

- **Consumer da Fila (consumer.py)**  
  - Arquivo: `consumer.py`  
  - Processo separado em Python que fica lendo mensagens da fila (long polling).  
  - Para cada mensagem, envia um e-mail usando SMTP (Gmail) e depois remove a mensagem da fila ou muda a visibilidade.

- **Infraestrutura/Deploy (systemd + scripts)**  
  - Arquivos: `flask-queue.service`, `flask-queue-consumer.service`, `scripts/deploy.sh`  
  - Automatizam a execução da aplicação em um servidor Linux (OCI), com serviços que sobem automaticamente e um script de deploy via SSH.

Fluxo resumido:

1. Usuário acessa `http://localhost:5002` ou a URL em produção.  
2. Frontend envia requisições `POST /publicar` ou `POST /publicar-canal` para o Flask.  
3. Flask faz uma chamada ao OCI Queue Service e coloca a mensagem na fila.  
4. O `consumer.py` fica rodando em loop, buscando mensagens na fila.  
5. Para cada mensagem, o consumer envia um e-mail com o conteúdo recebido.  
6. Se o e-mail foi enviado com sucesso, a mensagem é removida da fila; se falhar, a mensagem volta a ficar visível após um tempo.

---

## 2. Detalhes do Backend Flask – `app.py`

Arquivo: `app.py`

### 2.1. Importações principais

- `from flask import Flask, render_template, request, jsonify`  
  - `Flask`: cria a aplicação web.  
  - `render_template`: renderiza o HTML do diretório `templates`.  
  - `request`: acessa dados enviados pelo cliente (JSON, formulário).  
  - `jsonify`: retorna respostas JSON para o frontend.

- `import oci`  
  - SDK oficial da Oracle Cloud Infrastructure em Python.  
  - Usado para conectar na fila, enviar mensagens e consultar estatísticas.

- `import json`  
  - Conversão entre objetos Python e JSON (string) para enviar conteúdo para a fila.

- `import requests`  
  - (Importado, mas não está sendo usado atualmente).

- `from datetime import datetime`  
  - Usado para registros de data/hora (opcional neste arquivo).

### 2.2. Criação da aplicação Flask

```python
app = Flask(__name__)
```

Isso instancia a aplicação Flask. A partir desse objeto `app`, definimos as rotas (`@app.route`).

### 2.3. Configuração da conexão com a OCI Queue

```python
config = oci.config.from_file()
queue_client = oci.queue.QueueClient(config)
```

- `oci.config.from_file()`  
  - Lê as credenciais da OCI a partir do arquivo `~/.oci/config` (por padrão).  
  - Nesse arquivo ficam: `user`, `fingerprint`, `tenancy`, `region`, `key_file`, etc.  
  - A seção padrão geralmente é `[DEFAULT]`.

- `oci.queue.QueueClient(config)`  
  - Cria um cliente para trabalhar com o serviço de fila usando as credenciais lidas.

```python
queue_id = "ocid1.queue.oc1.sa-saopaulo-1.amaaaaaak6s5riqam3ccheibdo2op4ej5rp57m7w7kwre4ypzxc73rk36eca"
queue_endpoint = "https://cell-1.queue.messaging.sa-saopaulo-1.oci.oraclecloud.com"
queue_client.base_client.endpoint = queue_endpoint
```

- `queue_id`  
  - OCID da fila criada na OCI. É o identificador único da fila.

- `queue_endpoint`  
  - Endpoint específico do serviço de filas na região `sa-saopaulo-1`.

- `queue_client.base_client.endpoint = queue_endpoint`  
  - Sobrescreve o endpoint padrão do cliente para usar este endpoint específico.

### 2.4. Rota `/` – Interface web

```python
@app.route('/')
def index():
    return render_template('index.html')
```

- Quando o usuário acessa `/`, o Flask devolve o template `templates/index.html`.  
- Esse HTML carrega o CSS e o JavaScript que fazem a interface funcionar.

### 2.5. Rota `POST /publicar` – Enviar mensagem para a fila

```python
@app.route('/publicar', methods=['POST'])
def publicar():
    ...
```

Fluxo interno:

1. Lê o corpo JSON da requisição:
   ```python
   data = request.get_json()
   email = data.get('email')
   mensagem = data.get('mensagem')
   ```

2. Validação simples:
   - Se `email` ou `mensagem` estiverem vazios, retorna erro 400:
     ```python
     return jsonify({'error': 'Email e mensagem são obrigatórios'}), 400
     ```

3. Monta o objeto que será enviado para a fila:
   ```python
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
   ```

   - `PutMessagesDetails` representa o lote de mensagens a serem publicadas.  
   - `PutMessagesDetailsEntry` representa cada mensagem.  
   - `content` recebe uma string JSON com `email` e `msg`.

4. Envia a mensagem para a fila:
   ```python
   result = queue_client.put_messages(
       queue_id=queue_id,
       put_messages_details=put_messages_details
   )
   ```

   - O SDK faz a chamada HTTPS assinada com as credenciais da OCI.  
   - Se der certo, `result.data.messages[0].id` contém o ID da mensagem.

5. Retorna resposta para o frontend:
   ```python
   return jsonify({
       'message': 'Mensagem enviada para a fila com sucesso!',
       'id': result.data.messages[0].id
   }), 200
   ```

6. Tratamento de erros:
   ```python
   except Exception as e:
       print(f"Erro ao publicar mensagem: {e}")
       return jsonify({'error': str(e)}), 500
   ```

   - Qualquer exceção é capturada, logada no terminal e devolvida uma resposta 500.

### 2.6. Rota `POST /publicar-canal` – Enviar mensagem para canal específico

```python
@app.route('/publicar-canal', methods=['POST'])
def publicar_canal():
    ...
```

Diferenças em relação a `/publicar`:

1. Lê também o campo `canal` (com valor padrão `'canal1'`):
   ```python
   canal = data.get('canal', 'canal1')
   ```

2. Inclui metadados de canal na mensagem:
   ```python
   metadata=oci.queue.models.MessageMetadata(
       channel_id=canal
   )
   ```

3. Continua usando `queue_client.put_messages`, mas agora com `metadata` preenchido.

4. Resposta de sucesso menciona o canal:
   ```python
   'message': f'Mensagem enviada para o canal {canal} com sucesso!'
   ```

Na prática, isso permite segmentar mensagens dentro da mesma fila, usando “canais”.

### 2.7. Rota `GET /stats` – Estatísticas da fila

```python
@app.route('/stats', methods=['GET'])
def stats():
    ...
```

Fluxo:

1. Cria um cliente administrativo da fila:
   ```python
   queue_admin_client = oci.queue.QueueAdminClient(config)
   ```

2. Busca informações da fila:
   ```python
   queue_info = queue_admin_client.get_queue(queue_id=queue_id)
   ```

3. Retorna JSON com alguns dados:
   ```python
   return jsonify({
       'nome': queue_info.data.display_name,
       'estado': queue_info.data.lifecycle_state,
       'criado': str(queue_info.data.time_created),
       'regiao': 'sa-saopaulo-1'
   }), 200
   ```

4. Em caso de erro, retorna mensagem de erro com código 500.

### 2.8. Execução da aplicação Flask

```python
if __name__ == '__main__':
    print("=== Sistema de Fila OCI ===")
    ...
    app.run(debug=True, host='0.0.0.0', port=5002)
```

- `if __name__ == '__main__':`  
  - Bloco que só é executado quando rodamos `python app.py` diretamente.  
  - Se o arquivo for importado como módulo, esse bloco não roda.

- `app.run(debug=True, host='0.0.0.0', port=5002)`  
  - Inicia o servidor Flask no modo de desenvolvimento, escutando na porta 5002 em todas as interfaces de rede.

---

## 3. Detalhes do Consumer – `consumer.py`

Arquivo: `consumer.py`

O `consumer.py` é um script Python que roda continuamente, consumindo mensagens da fila e enviando e-mails.

### 3.1. Importações principais

- `import oci` – para acessar a fila.  
- `import json` – para decodificar o conteúdo das mensagens.  
- `import time` – para usar `sleep` entre as iterações.  
- `import smtplib` – cliente SMTP para envio de e-mail.  
- `from email.mime.text import MIMEText`  
- `from email.mime.multipart import MIMEMultipart`  
  - Constrói o e-mail em formato MIME (permitindo HTML).  
- `from datetime import datetime` – para logs com horário.

### 3.2. Configuração de OCI

Mesma lógica do `app.py`:

```python
config = oci.config.from_file()
queue_client = oci.queue.QueueClient(config)
queue_id = "..."  # mesmo OCID da fila
queue_endpoint = "https://cell-1.queue.messaging.sa-saopaulo-1.oci.oraclecloud.com"
queue_client.base_client.endpoint = queue_endpoint
```

### 3.3. Configuração de e-mail

```python
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = 'seu-email@gmail.com'
EMAIL_PASS = 'sua-app-password'
```

- Usa Gmail como servidor SMTP.  
- Porta 587 com TLS.  
- Importante: na prática, o ideal é **não** deixar senha em texto plano no código, mas usar variáveis de ambiente ou um arquivo de configuração seguro.

### 3.4. Função `enviar_email`

```python
def enviar_email(assunto, destinatario, corpo_html):
    ...
```

Passos:

1. Cria um objeto `MIMEMultipart('alternative')` para permitir conteúdo em HTML.  
2. Define cabeçalhos `Subject`, `From` e `To`.  
3. Cria um `MIMEText(corpo_html, 'html')` e anexa ao e-mail.  
4. Abre conexão com `smtplib.SMTP(SMTP_SERVER, SMTP_PORT)`.  
5. Inicia TLS com `server.starttls()`.  
6. Faz login com `server.login(EMAIL_USER, EMAIL_PASS)`.  
7. Envia a mensagem com `server.send_message(msg)`.  
8. Trata exceções, imprimindo mensagens de sucesso/erro e retornando `True` ou `False`.

### 3.5. Função `processar_mensagem`

```python
def processar_mensagem(mensagem):
    ...
```

Parâmetro `mensagem` é um objeto retornado pelo `queue_client.get_messages`.

Fluxo:

1. Converte o conteúdo da mensagem de JSON para Python:
   ```python
   conteudo = json.loads(mensagem.content)
   email = conteudo.get('email')
   msg = conteudo.get('msg')
   receipt = mensagem.receipt
   ```

2. Imprime logs amigáveis com horário, e-mail e parte da mensagem.  

3. Chama `enviar_email("Mensagem da Fila OCI", email, msg)`.  

4. Se **sucesso**:
   - Remove a mensagem da fila:
     ```python
     queue_client.delete_message(
         queue_id=queue_id,
         message_receipt=receipt
     )
     ```
   - Retorna `True`.

5. Se **falha** ao enviar o e-mail:
   - Atualiza a visibilidade da mensagem para 30 segundos:
     ```python
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
     ```
   - Isso significa que a mensagem volta a ficar visível para ser reprocessada depois.  
   - Retorna `False`.

6. Em caso de exceção geral, imprime o erro e retorna `False`.

### 3.6. Função `consumir_fila`

```python
def consumir_fila():
    ...
```

Responsável pelo loop infinito:

1. Imprime cabeçalho com informações da fila e do e-mail.  
2. Inicializa contador `mensagens_processadas = 0`.  
3. Loop `while True:`:
   - Tenta buscar mensagens:
     ```python
     get_messages_response = queue_client.get_messages(
         queue_id=queue_id,
         limit=10,
         timeout_in_seconds=30
     )
     ```
   - `limit=10` – até 10 mensagens por vez.  
   - `timeout_in_seconds=30` – long polling (espera até 30s por mensagens).
   - Obtém a lista de mensagens:
     ```python
     mensagens = get_messages_response.data.messages
     ```
   - Se houver mensagens, processa uma a uma com `processar_mensagem(mensagem)`.  
   - Incrementa `mensagens_processadas` para cada mensagem processada com sucesso.  
   - Imprime estatísticas no terminal.
   - `time.sleep(2)` – pequeno delay para evitar sobrecarregar o serviço.

4. Tratamento de interrupção manual (`Ctrl+C`):
   - Captura `KeyboardInterrupt`, mostra o total processado e finaliza o loop.

5. Tratamento de outros erros:
   - Em caso de exceção, imprime o erro e espera 5 segundos (`time.sleep(5)`) antes de tentar de novo.

### 3.7. Execução direta

```python
if __name__ == '__main__':
    consumir_fila()
```

Quando rodamos `python consumer.py`, o script entra diretamente em `consumir_fila()` e começa a consumir a fila.

---

## 4. Frontend – HTML, CSS e JavaScript

### 4.1. Template HTML – `templates/index.html`

Principais elementos:

- Navbar com o título **OCI Queue Manager**.  
- Três cards de estatísticas:
  - Nome da fila (`#queueName`).  
  - Status (`#queueStatus`).  
  - Região (`#queueRegion`).  
- Seção de envio de mensagens com duas abas:
  - **Fila Normal** – formulário `formNormal` (email + mensagem).  
  - **Com Canal** – formulário `formCanal` (email, canal, mensagem).
- Div de toast (`#toast`) para notificações de sucesso/erro.

O HTML carrega:

- `static/css/style.css` – estilos visuais.  
- Font Awesome – ícones.  
- `static/js/app.js` – lógica de frontend.

### 4.2. JavaScript – `static/js/app.js`

Pontos principais:

- `document.addEventListener('DOMContentLoaded', ...)`  
  - Ao carregar a página, chama `carregarStats()` e `configurarFormularios()`.

- `async function carregarStats()`  
  - Faz `fetch('/stats')`.  
  - Preenche os elementos `queueName`, `queueStatus` e `queueRegion` com os dados retornados pelo Flask.  
  - Em caso de erro, mostra `Erro` nos campos.

- `function configurarFormularios()`  
  - Adiciona listeners de `submit` para `formNormal` e `formCanal`.  
  - Impede o comportamento padrão (`e.preventDefault()`).  
  - Chama `publicarMensagem(...)` com os dados do formulário.

- `async function publicarMensagem(email, mensagem, usarCanal = false, canal = null)`  
  - Decide o endpoint:
    - Se `usarCanal` é `false` → `/publicar`.  
    - Se `usarCanal` é `true` → `/publicar-canal`.  
  - Monta o `payload` JSON com `email`, `mensagem` e, opcionalmente, `canal`.  
  - Faz `fetch(endpoint, { method: 'POST', headers: {...}, body: JSON.stringify(payload) })`.  
  - Mostra um spinner no botão enquanto envia.  
  - Em caso de sucesso, mostra toast de sucesso e limpa os campos.  
  - Em caso de erro, mostra toast de erro.

- `function selecionarTab(tab)`  
  - Alterna visualmente entre a aba da fila normal e da fila com canal.

- `function mostrarToast(mensagem, tipo = 'success')`  
  - Controla a exibição da notificação (`#toast`), adicionando classes CSS para animação e removendo depois de 3 segundos.

### 4.3. CSS – `static/css/style.css`

Responsável por:

- Layout responsivo.  
- Estilo dos cards de estatísticas.  
- Estilos dos formulários, botões, abas e toasts.  
- Aparência moderna da interface.

---

## 5. Serviços systemd e Deploy

### 5.1. Serviços systemd

Arquivos: `flask-queue.service`, `flask-queue-consumer.service`

Ambos têm estrutura semelhante:

- `[Unit]`
  - `Description` – descrição do serviço.  
  - `After=network.target` – só inicia depois da rede estar disponível.

- `[Service]`
  - `Type=simple` – processo simples em foreground.  
  - `User=opc` – usuário do sistema que roda o serviço.  
  - `WorkingDirectory=/home/opc/fila-python` – diretório onde está o projeto.  
  - Variáveis de ambiente (`PATH`, `VIRTUAL_ENV`, `PYTHONPATH`) apontando para o virtualenv.  
  - `ExecStart=/usr/bin/python3.9 /home/opc/fila-python/app.py` ou `consumer.py`.  
  - `Restart=always` e `RestartSec=10` – tenta reiniciar o serviço em caso de falha.

- `[Install]`
  - `WantedBy=multi-user.target` – permite habilitar o serviço para iniciar automaticamente no boot.

Na prática:

- `flask-queue.service` roda o servidor Flask (`app.py`).  
- `flask-queue-consumer.service` roda o consumer (`consumer.py`).

### 5.2. Script de deploy – `scripts/deploy.sh`

Função principal: enviar o código do projeto para uma instância OCI e reiniciar os serviços.

Passos principais:

1. Lê variáveis:
   - `INSTANCE_IP` – IP da instância remota (pode vir do ambiente).  
   - `SSH_KEY` – caminho da chave privada usada para conectar via SSH.  
   - `REMOTE_USER="opc"` – usuário padrão.  
   - `APP_DIR="/home/opc/fila-python"` – diretório da aplicação no servidor.

2. Verifica se a chave SSH existe.  

3. Para os serviços remotos:
   ```bash
   sudo systemctl stop flask-queue flask-queue-consumer
   ```

4. Copia arquivos da aplicação para o servidor (via `scp`):
   - `app.py`, `consumer.py`, `requirements.txt`, `templates/`, `static/`.

5. Se houver diretório `.oci/` local, copia para `/home/opc/.oci/` no servidor e ajusta o caminho da chave no arquivo `config` com `sed`.

6. No servidor, ativa o virtualenv (`/home/opc/venv`) e roda:
   ```bash
   pip install --upgrade -r /home/opc/fila-python/requirements.txt
   ```

7. Reinicia os serviços:
   ```bash
   sudo systemctl start flask-queue flask-queue-consumer
   ```

8. Mostra o status dos serviços e a URL de acesso.

---

## 6. Conceitos de Python usados no projeto

### 6.1. Estrutura de script Python

- Cada arquivo (`app.py`, `consumer.py`) é tanto:
  - Um **módulo** (poderia ser importado por outro Python).  
  - Quanto um **script executável** (quando rodado diretamente).

- O bloco:
  ```python
  if __name__ == '__main__':
      ...
  ```
  garante que a lógica principal só rode quando o arquivo for executado diretamente.

### 6.2. Funções

- Funções como `enviar_email`, `processar_mensagem`, `consumir_fila`, `publicar`, `publicar_canal`:
  - Encapsulam lógica específica.  
  - Facilitam reutilização e testes.  
  - Tornam o código mais organizado e fácil de explicar.

### 6.3. Tratamento de exceções (`try/except`)

- Utilizado em vários pontos:
  - Ao publicar mensagens na fila.  
  - Ao enviar e-mails.  
  - No loop principal do consumer.

Benefícios:

- Evita que o programa quebre completamente em caso de erro.  
- Permite logar mensagens de erro claras.  
- No consumer, permite tentar de novo após um tempo.

### 6.4. Trabalhando com JSON

- `json.dumps(obj)` – converte um dicionário Python em string JSON (usado para `content` da mensagem da fila).  
- `json.loads(str_json)` – converte string JSON recebida da fila de volta para dicionário Python.

### 6.5. Programação assíncrona no frontend (não em Python, mas importante)

- As funções `async`/`await` usadas em `static/js/app.js` permitem:
  - Fazer requisições HTTP sem travar a interface do usuário.  
  - Esperar o resultado das operações de rede de forma clara.

---

## 7. Como explicar o sistema para alguém

Uma forma simples de explicar:

1. **“Temos uma aplicação web em Flask (Python)** que deixa o usuário enviar uma mensagem para uma fila na Oracle Cloud (OCI).  
2. **Essa mensagem cai numa fila gerenciada pela OCI**, identificada por um OCID e acessada via SDK Python.  
3. **Em paralelo, um segundo programa Python (consumer)** fica rodando em loop e buscando mensagens nessa fila.  
4. **Cada mensagem contém um e-mail e um texto**. O consumer pega isso, monta um e-mail e envia via SMTP (Gmail).  
5. **Se o e-mail foi enviado com sucesso**, a mensagem é removida da fila. Se houve erro, a mensagem volta a ficar disponível depois de um tempo para tentar de novo.  
6. **Tudo isso roda em um servidor Linux**, onde usamos serviços `systemd` para garantir que tanto a API Flask quanto o consumer iniciem automaticamente e fiquem sempre no ar.  
7. **Um script de deploy (`scripts/deploy.sh`) facilita enviar o código atualizado para o servidor**, parar os serviços, atualizar dependências e subir tudo novamente.

Com essa visão e os detalhes deste documento, você consegue navegar pelo código e responder perguntas sobre:

- Onde a fila é configurada.  
- Como é feita a autenticação OCI.  
- Como as mensagens são criadas e enviadas.  
- Como o consumer lê, processa e trata erros.  
- Como a interface web conversa com o backend.  
- Como a aplicação é executada em produção.

---

Se quiser, posso também gerar um resumo em forma de slides ou tópicos enxutos para apresentação oral.

