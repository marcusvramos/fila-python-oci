// Estado da aplicação
let tabAtual = 'normal';

// Inicializar quando o DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    carregarStats();
    configurarFormularios();
});

/**
 * Carregar estatísticas da fila
 */
async function carregarStats() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();

        if (response.ok) {
            document.getElementById('queueName').textContent = data.nome;
            document.getElementById('queueStatus').textContent = data.estado;
            document.getElementById('queueRegion').textContent = data.regiao;
        } else {
            throw new Error(data.error || 'Erro ao carregar estatísticas');
        }
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('queueName').textContent = 'Erro';
        document.getElementById('queueStatus').textContent = 'Erro';
        document.getElementById('queueRegion').textContent = 'Erro';
    }
}

/**
 * Configurar formulários
 */
function configurarFormularios() {
    // Formulário normal
    document.getElementById('formNormal').addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('emailNormal').value;
        const mensagem = document.getElementById('mensagemNormal').value;

        await publicarMensagem(email, mensagem, false);
    });

    // Formulário com canal
    document.getElementById('formCanal').addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('emailCanal').value;
        const mensagem = document.getElementById('mensagemCanal').value;
        const canal = document.getElementById('canalId').value;

        await publicarMensagem(email, mensagem, true, canal);
    });
}

/**
 * Publicar mensagem na fila
 */
async function publicarMensagem(email, mensagem, usarCanal = false, canal = null) {
    const btnSubmit = event.target.querySelector('button[type="submit"]');
    const textoBotaoOriginal = btnSubmit.innerHTML;

    try {
        // Mostrar loading
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';

        const endpoint = usarCanal ? '/publicar-canal' : '/publicar';
        const payload = { email, mensagem };

        if (usarCanal && canal) {
            payload.canal = canal;
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            mostrarToast(data.message, 'success');

            // Limpar formulário
            if (usarCanal) {
                document.getElementById('emailCanal').value = '';
                document.getElementById('mensagemCanal').value = '';
            } else {
                document.getElementById('emailNormal').value = '';
                document.getElementById('mensagemNormal').value = '';
            }
        } else {
            throw new Error(data.error || 'Erro ao publicar mensagem');
        }

    } catch (error) {
        console.error('Erro:', error);
        mostrarToast(error.message, 'error');
    } finally {
        // Restaurar botão
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = textoBotaoOriginal;
    }
}

/**
 * Selecionar tab
 */
function selecionarTab(tab) {
    // Atualizar estado
    tabAtual = tab;

    // Atualizar botões
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Atualizar conteúdo
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    if (tab === 'normal') {
        document.getElementById('tabNormal').classList.add('active');
    } else {
        document.getElementById('tabCanal').classList.add('active');
    }
}

/**
 * Mostrar notificação toast
 */
function mostrarToast(mensagem, tipo = 'success') {
    const toast = document.getElementById('toast');

    // Ícones por tipo
    const icones = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    toast.innerHTML = `<i class="${icones[tipo]}"></i> ${mensagem}`;
    toast.className = `toast ${tipo} show`;

    // Remover após 3 segundos
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

/**
 * Validação de e-mail
 */
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}
