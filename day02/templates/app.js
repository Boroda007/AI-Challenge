// ===== DOM =====
const form = document.getElementById('chatForm');
const input = document.getElementById('userInput');
const container = document.getElementById('chats-container');

// ===== История =====
const freeChatHistory = [];
const controlledChatHistory = [];

// ===== Утилиты =====
function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function scrollToBottom() {
    container.scrollTop = container.scrollHeight;
}

// ===== Рендер строки диалога =====
function addTurn(userText, freeHtml, controlledHtml, finishReason, appliedParams, freeUsage, controlledUsage) {
    const row = document.createElement('div');
    row.className = 'chat-row';

    // Левая колонка: ответ ИИ (свободный)
    const cellLeft = document.createElement('div');
    cellLeft.className = 'chat-ai-left';
    let leftContent = `<div class="message ai"><div class="bubble">${freeHtml}</div></div>`;
    if (freeUsage) {
        leftContent += `<div class="token-count">${freeUsage.completion} токенов</div>`;
    }
    cellLeft.innerHTML = leftContent;

    // Центральная колонка: сообщение пользователя
    const cellUser = document.createElement('div');
    cellUser.className = 'chat-user';
    cellUser.innerHTML = `<div class="message user"><div class="bubble">${escapeHtml(userText)}</div></div>`;

    // Правая колонка: ответ ИИ (контролируемый) + параметры
    const cellRight = document.createElement('div');
    cellRight.className = 'chat-ai-right';
    let rightContent = `<div class="message ai"><div class="bubble">${controlledHtml}</div></div>`;

    // Собираем бейджи параметров
    let badges = '';

    // Причина остановки — первый бейдж
    if (finishReason) {
        const reasonMap = { stop: 'Стоп-символ', length: 'Длина', content_filter: 'Фильтр' };
        const reasonLabel = reasonMap[finishReason] || finishReason;
        badges += `<span class="param-badge param-badge--reason">Причина остановки: ${escapeHtml(reasonLabel)}</span>`;
    }

    // Сработавшие инженерные параметры
    if (appliedParams && typeof appliedParams === 'object') {
        for (const [name, value] of Object.entries(appliedParams)) {
            if (value !== null && value !== undefined) {
                badges += `<span class="param-badge">${escapeHtml(name)}: ${escapeHtml(String(value))}</span>`;
            }
        }
    }

    if (badges) {
        rightContent += `<div class="params-block">${badges}</div>`;
    }

    if (controlledUsage) {
        rightContent += `<div class="token-count">${controlledUsage.completion} токенов</div>`;
    }

    cellRight.innerHTML = rightContent;

    row.appendChild(cellLeft);
    row.appendChild(cellUser);
    row.appendChild(cellRight);
    container.appendChild(row);

    scrollToBottom();
}

// ===== Логика чекбоксов: disabled-состояние =====
document.querySelectorAll('.setting-row[data-param]').forEach(row => {
    const cb = row.querySelector('input[type="checkbox"]');
    cb.addEventListener('change', () => {
        row.classList.toggle('disabled', !cb.checked);
        row.querySelectorAll('select, input[type="text"], input[type="range"], textarea').forEach(el => {
            el.disabled = !cb.checked;
        });
        const layout = row.closest('.prompt-layout');
        if (layout) {
            const ta = layout.querySelector('.prompt-textarea');
            if (ta) ta.disabled = !cb.checked;
        }
    });
});

// ===== Слайдеры: обновление числового индикатора =====
document.getElementById('rng-maxtokens').addEventListener('input', e => {
    document.getElementById('val-maxtokens').textContent = e.target.value;
});
document.getElementById('rng-temp').addEventListener('input', e => {
    document.getElementById('val-temp').textContent = e.target.value;
});

// ===== Сбор данных с панели настроек =====
function collectConstraints() {
    const c = {};
    if (document.getElementById('cb-format').checked) {
        const formatMap = { text: 'text', json: 'json_object' };
        c.response_format = { type: formatMap[document.getElementById('sel-format').value] };
    }
    if (document.getElementById('cb-maxtokens').checked)
        c.max_tokens = parseInt(document.getElementById('rng-maxtokens').value, 10);
    if (document.getElementById('cb-stop').checked) {
        const v = document.getElementById('txt-stop').value.trim();
        if (v) c.stop = v;
    }
    if (document.getElementById('cb-temp').checked)
        c.temperature = parseFloat(document.getElementById('rng-temp').value);
    if (document.getElementById('cb-sysprompt').checked) {
        const v = document.getElementById('txt-sysprompt').value.trim();
        if (v) c.system_prompt = v;
    }
    return c;
}

// ===== Отправка и обработка =====
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    // Добавляем сообщение пользователя в оба потока истории
    freeChatHistory.push({ role: 'user', content: text });
    controlledChatHistory.push({ role: 'user', content: text });

    // Блокируем ввод на время запроса
    input.disabled = true;
    form.querySelector('button').disabled = true;

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                free_history: freeChatHistory,
                controlled_history: controlledChatHistory,
                constraints: collectConstraints(),
            }),
        });

        const data = await resp.json();

        if (data.error) {
            const errMsg = `Ошибка: ${escapeHtml(data.error)}`;
            addTurn(text, errMsg, errMsg, null);
            return;
        }

        // Сохраняем ответы в историю
        freeChatHistory.push({ role: 'assistant', content: data.free_response.content });
        controlledChatHistory.push({ role: 'assistant', content: data.controlled_response.content });

        // Рендерим одну строку с тремя колонками
        addTurn(
            text,
            data.free_response.content,
            data.controlled_response.content,
            data.controlled_response.finish_reason,
            data.controlled_response.applied_params,
            data.free_response.usage,
            data.controlled_response.usage,
        );

    } catch (err) {
        const errMsg = `Ошибка сети: ${escapeHtml(err.message)}`;
        addTurn(text, errMsg, errMsg, null);
    } finally {
        input.disabled = false;
        form.querySelector('button').disabled = false;
        input.focus();
    }
});
