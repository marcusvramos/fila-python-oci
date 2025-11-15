# OCI Queue Manager - Sistema de Fila Python

Sistema de gerenciamento de filas OCI (Oracle Cloud Infrastructure) com interface web moderna e consumer em tempo real.

## 🚀 Funcionalidades

- **Interface Web Moderna**: Dashboard com estatísticas em tempo real
- **Publicação de Mensagens**: Envie mensagens para a fila OCI
- **Suporte a Canais**: Segmente mensagens usando canais específicos
- **Consumer Automático**: Processa mensagens continuamente
- **Envio de E-mails**: Integração com Gmail para envio automático
- **Design Responsivo**: Interface adaptável para todos os dispositivos

## 📋 Pré-requisitos

- Python 3.8+
- Conta Oracle Cloud com Queue Service configurado
- Credenciais OCI em `~/.oci/config`
- Conta Gmail com App Password configurado

## 🔧 Instalação

1. **Clone ou navegue até o diretório do projeto:**
```bash
cd "/Users/marcusramos/Documents/Faculdade/8 Termo/TTC3/fila-python"
```

2. **Instale as dependências:**
```bash
pip3 install -r requirements.txt
```

3. **Configure as credenciais OCI:**
Certifique-se de que o arquivo `~/.oci/config` está configurado corretamente.

4. **Configure o e-mail no consumer.py:**
Edite as linhas 26-27 com suas credenciais:
```python
EMAIL_USER = 'seu-email@gmail.com'
EMAIL_PASS = 'sua-app-password'
```

## 🎮 Como Usar

### 1. Iniciar a Aplicação Web

Em um terminal:
```bash
python3 app.py
```

A aplicação estará disponível em: **http://localhost:5002**

### 2. Iniciar o Consumer

Em outro terminal:
```bash
python3 consumer.py
```

O consumer ficará rodando continuamente, processando mensagens da fila.

### 3. Usar a Interface Web

1. Acesse http://localhost:5002
2. Escolha entre "Fila Normal" ou "Com Canal"
3. Preencha o e-mail e a mensagem
4. Clique em "Enviar"
5. O consumer processará automaticamente e enviará o e-mail

## 📁 Estrutura do Projeto

```
fila-python/
├── app.py                  # Aplicação Flask (Web Server)
├── consumer.py             # Consumer de mensagens (Loop contínuo)
├── requirements.txt        # Dependências Python
├── README.md              # Esta documentação
├── templates/
│   └── index.html         # Template HTML
└── static/
    ├── css/
    │   └── style.css      # Estilos CSS
    └── js/
        └── app.js         # JavaScript da aplicação
```

## 🔐 Configuração OCI

O sistema usa as seguintes configurações OCI:

- **Queue ID**: `ocid1.queue.oc1.sa-saopaulo-1.amaaaaaak6s5riqam3ccheibdo2op4ej5rp57m7w7kwre4ypzxc73rk36eca`
- **Região**: São Paulo (sa-saopaulo-1)
- **Endpoint**: `https://cell-1.queue.messaging.sa-saopaulo-1.oci.oraclecloud.com`

## 📧 Configuração de E-mail

Para usar o Gmail, você precisa:

1. Ativar verificação em duas etapas
2. Gerar uma App Password em: https://myaccount.google.com/apppasswords
3. Usar a App Password gerada no arquivo `consumer.py`

## 🎯 Endpoints da API

### GET /
Interface web principal

### POST /publicar
Publica uma mensagem na fila normal
```json
{
  "email": "destinatario@email.com",
  "mensagem": "Sua mensagem aqui"
}
```

### POST /publicar-canal
Publica uma mensagem em um canal específico
```json
{
  "email": "destinatario@email.com",
  "mensagem": "Sua mensagem aqui",
  "canal": "canal1"
}
```

### GET /stats
Retorna estatísticas da fila
```json
{
  "nome": "fila-mensagens",
  "estado": "ACTIVE",
  "criado": "2025-11-12T22:53:57.207000+00:00",
  "regiao": "sa-saopaulo-1"
}
```

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Cloud**: Oracle Cloud Infrastructure (OCI)
- **Queue**: OCI Queue Service
- **E-mail**: SMTP Gmail
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Icons**: Font Awesome 6.4.0

## 📝 Notas

- O consumer processa até 10 mensagens por vez
- Mensagens falhas são recolocadas na fila (30 segundos)
- O sistema usa long polling (30 segundos) para otimizar recursos
- Todas as mensagens são armazenadas em formato JSON

## 🐛 Troubleshooting

**Erro de autenticação OCI:**
- Verifique o arquivo `~/.oci/config`
- Confirme que o arquivo PEM existe e tem permissões corretas

**Erro ao enviar e-mail:**
- Verifique se a App Password está correta
- Confirme que a verificação em 2 etapas está ativa

**Consumer não processa mensagens:**
- Verifique se há mensagens na fila
- Confirme que o endpoint está correto
- Verifique os logs no terminal

## 👨‍💻 Autor

Sistema desenvolvido para TTC3 - 8º Termo
Faculdade UNOESTE

## 🚀 Deploy em Produção

A aplicação está configurada para deploy em OCI com suporte a HTTPS via Let's Encrypt.

### URLs em Produção
- **Aplicação de Fila**: https://queue.144.22.230.225.nip.io/
- **Aplicação de Fotos**: https://144.22.230.225.nip.io/

### Deploy Rápido

```bash
# Setup inicial (primeira vez)
./scripts/setup-server.sh
./scripts/setup-ssl.sh

# Deploy de atualizações
./scripts/deploy.sh
```

Para instruções completas de deploy, consulte [DEPLOY.md](DEPLOY.md).

## 📄 Licença

Este projeto é para fins educacionais.
