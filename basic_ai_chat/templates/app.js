// ===== DOM =====
const input = document.getElementById('userInput');
const container = document.getElementById('chats-container');
const cbFreeChat = document.getElementById('cb-free-chat');
const btnSendChat = document.getElementById('btn-send-chat');
const txtSysprompt = document.getElementById('txt-sysprompt');
const btnSendPrompt = document.getElementById('btn-send-prompt');
const selReasoning = document.getElementById('sel-reasoning');
const cbReasoning = document.getElementById('cb-reasoning');

// ===== Раскладка =====
function updateLayoutVars() {
    const header = document.querySelector('.header');
    const bottomPanel = document.querySelector('.bottom-panel');
    if (header) document.documentElement.style.setProperty('--header-h', header.offsetHeight + 'px');
    if (bottomPanel) document.documentElement.style.setProperty('--bottom-h', bottomPanel.offsetHeight + 'px');
}

// ===== История =====
const freeChatHistory = [];
const controlledChatHistory = [];

// ===== Состояние =====
let freeChatEnabled = false;

// ===== Утилиты =====
function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function scrollToBottom() {
    const mainArea = document.querySelector('.main-area');
    if (mainArea) mainArea.scrollTop = mainArea.scrollHeight;
}

// ===== Загрузка конфигурации =====
async function loadConfig() {
    try {
        const valuesResp = await fetch('/api/supported-values');
        const values = await valuesResp.json();

        // Обновляем reasoning_effort select
        updateReasoningSelect(values.reasoning_effort || []);

        // Обновляем слайдеры temperature и max_tokens
        updateSlider('rng-temp', 'val-temp', values.temperature);
        updateSlider('rng-maxtokens', 'val-maxtokens', values.max_tokens);
    } catch (err) {
        console.error('Ошибка загрузки конфигурации:', err);
    }
}

function updateReasoningSelect(values) {
    selReasoning.innerHTML = '';
    const row = selReasoning.closest('.setting-row');
    if (!values || values.length === 0) {
        // Скрываем строку если параметр не поддерживается
        if (row) row.style.display = 'none';
        return;
    }
    if (row) row.style.display = '';

    for (const v of values) {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        selReasoning.appendChild(opt);
    }

    // Если модель поддерживает "none" — включаем параметр по умолчанию,
    // чтобы рассуждения были выключены (иначе дефолт провайдера тратит токены)
    if (values.includes('none')) {
        selReasoning.value = 'none';
        cbReasoning.checked = true;
        if (row) row.classList.remove('disabled');
        selReasoning.disabled = false;
    }
}

function updateSlider(sliderId, displayId, config) {
    if (!config || !config.min === undefined) return;
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (!slider) return;

    slider.min = config.min;
    slider.max = config.max;
    slider.step = config.step || 0.1;
    slider.value = config.default;
    if (display) display.textContent = config.default;
}

// ===== Panel tabs =====
const freeChatToggle = document.querySelector('.free-chat-toggle');

document.querySelectorAll('.panel-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.panel-tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel-view').forEach(v => v.classList.remove('active'));
        btn.classList.add('active');
        document.querySelector(`[data-view="${btn.dataset.panel}"]`).classList.add('active');
        freeChatToggle.style.display = btn.dataset.panel === 'chat' ? '' : 'none';
        updateLayoutVars();
    });
});

// ===== Show/hide кнопок и авто-высота =====
function initButtonVisibility() {
    btnSendChat.disabled = !input.value.trim();
    btnSendPrompt.disabled = !txtSysprompt.value.trim();
}

input.addEventListener('input', () => {
    btnSendChat.disabled = !input.value.trim();
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
});

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

txtSysprompt.addEventListener('input', () => {
    btnSendPrompt.disabled = !txtSysprompt.value.trim();
    txtSysprompt.style.height = 'auto';
    txtSysprompt.style.height = txtSysprompt.scrollHeight + 'px';
});

// ===== Отправка системного промпта =====
btnSendPrompt.addEventListener('click', async () => {
    const prompt = txtSysprompt.value.trim();
    if (!prompt) return;

    const resp = await fetch('/api/system-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
    });
    const rawRequest = await resp.json();

    addSystemPromptTurn(prompt, rawRequest);

    btnSendPrompt.style.opacity = '0.5';
    btnSendPrompt.disabled = true;
    setTimeout(() => { btnSendPrompt.style.opacity = ''; btnSendPrompt.disabled = false; }, 1500);
});

// ===== Рендер строки диалога =====
function buildRawJson(rawApiResponse) {
    if (!rawApiResponse) return '';
    return JSON.stringify(rawApiResponse, null, 2);
}

function addTurn(userText, freeHtml, controlledHtml, finishReason, appliedParams, freeUsage, controlledUsage, showFree, rawFree, rawControlled, rawRequest) {
    // Сообщение пользователя (справа)
    const userRow = document.createElement('div');
    userRow.className = 'chat-row row-user';
    let userContent = `
        <div class="msg-label">Вы</div>
        <div class="message user"><div class="bubble">${escapeHtml(userText)}</div></div>
    `;
    if (rawRequest) {
        const rawJson = buildRawJson(rawRequest);
        userContent += `<details class="raw-json-toggle"><summary role="button" class="outline secondary">JSON-запрос</summary><pre><code>${escapeHtml(rawJson)}</code></pre></details>`;
    }
    userRow.innerHTML = userContent;
    container.appendChild(userRow);

    // Ответ ИИ (слева)
    const aiRow = document.createElement('div');
    aiRow.className = 'chat-row row-ai';

    let aiContent = ``;

    if (showFree && freeHtml) {
        // Два ответа рядом
        aiContent += `<div class="ai-responses">`;

        // Левая колонка: свободный ответ
        aiContent += `<div class="ai-response-col">`;
        aiContent += `<div class="msg-label">ИИ (без ограничений)</div>`;
        aiContent += `<div class="message ai"><div class="bubble">${freeHtml}</div></div>`;
        if (freeUsage) {
            aiContent += `<div class="params-row"><div class="token-count">${freeUsage.completion} токенов</div></div>`;
        }
        if (rawFree !== null && rawFree !== undefined) {
            const rawJson = buildRawJson(rawFree);
            aiContent += `<details class="raw-json-toggle"><summary role="button" class="outline secondary">JSON-ответ</summary><pre><code>${escapeHtml(rawJson)}</code></pre></details>`;
        }
        aiContent += `</div>`;

        // Правая колонка: контролируемый ответ
        aiContent += `<div class="ai-response-col">`;
        aiContent += `<div class="msg-label">ИИ</div>`;
        aiContent += `<div class="message ai"><div class="bubble">${controlledHtml}</div></div>`;

        // Бейджи + токены в одну строку
        aiContent += `<div class="params-row">`;

        let badges = '';
        if (finishReason) {
            const reasonMap = { stop: 'Стоп-символ', length: 'Длина', content_filter: 'Фильтр' };
            const reasonLabel = reasonMap[finishReason] || finishReason;
            badges += `<span class="param-badge param-badge--reason">Причина остановки: ${escapeHtml(reasonLabel)}</span>`;
        }
        if (appliedParams && typeof appliedParams === 'object') {
            for (const [name, value] of Object.entries(appliedParams)) {
                if (value !== null && value !== undefined) {
                    badges += `<span class="param-badge">${escapeHtml(name)}: ${escapeHtml(String(value))}</span>`;
                }
            }
        }
        if (badges) {
            aiContent += `<div class="params-block">${badges}</div>`;
        }

        if (controlledUsage) {
            aiContent += `<div class="token-count">${controlledUsage.completion} токенов</div>`;
        }

        aiContent += `</div>`; // params-row

        if (rawControlled !== null && rawControlled !== undefined) {
            const rawJson = buildRawJson(rawControlled);
            aiContent += `<details class="raw-json-toggle"><summary role="button" class="outline secondary">JSON-ответ</summary><pre><code>${escapeHtml(rawJson)}</code></pre></details>`;
        }

        aiContent += `</div>`; // ai-response-col
        aiContent += `</div>`; // ai-responses
    } else {
        // Один ответ на всю ширину
        aiContent += `<div class="ai-responses ai-responses--single">`;
        aiContent += `<div class="ai-response-col">`;
        aiContent += `<div class="msg-label">ИИ</div>`;
        aiContent += `<div class="message ai"><div class="bubble">${controlledHtml}</div></div>`;

        // Бейджи + токены в одну строку
        aiContent += `<div class="params-row">`;

        let badges = '';
        if (finishReason) {
            const reasonMap = { stop: 'Стоп-символ', length: 'Длина', content_filter: 'Фильтр' };
            const reasonLabel = reasonMap[finishReason] || finishReason;
            badges += `<span class="param-badge param-badge--reason">Причина остановки: ${escapeHtml(reasonLabel)}</span>`;
        }
        if (appliedParams && typeof appliedParams === 'object') {
            for (const [name, value] of Object.entries(appliedParams)) {
                if (value !== null && value !== undefined) {
                    badges += `<span class="param-badge">${escapeHtml(name)}: ${escapeHtml(String(value))}</span>`;
                }
            }
        }
        if (badges) {
            aiContent += `<div class="params-block">${badges}</div>`;
        }

        if (controlledUsage) {
            aiContent += `<div class="token-count">${controlledUsage.completion} токенов</div>`;
        }

        aiContent += `</div>`; // params-row

        if (rawControlled !== null && rawControlled !== undefined) {
            const rawJson = buildRawJson(rawControlled);
            aiContent += `<details class="raw-json-toggle"><summary role="button" class="outline secondary">JSON-ответ</summary><pre><code>${escapeHtml(rawJson)}</code></pre></details>`;
        }

        aiContent += `</div>`; // ai-response-col
        aiContent += `</div>`; // ai-responses
    }

    aiRow.innerHTML = aiContent;
    container.appendChild(aiRow);

    scrollToBottom();
}

// ===== Рендер системного промпта в чате =====
function addSystemPromptTurn(promptText, rawRequest) {
    const row = document.createElement('div');
    row.className = 'chat-row row-user';
    let content = `
        <div class="msg-label">Системный промпт</div>
        <div class="message user"><div class="bubble">${escapeHtml(promptText)}</div></div>
    `;
    if (rawRequest) {
        const rawJson = buildRawJson(rawRequest);
        content += `<details class="raw-json-toggle"><summary role="button" class="outline secondary">JSON-запрос</summary><pre><code>${escapeHtml(rawJson)}</code></pre></details>`;
    }
    row.innerHTML = content;
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
    });
});

// ===== Переключатель свободного чата =====
cbFreeChat.addEventListener('change', () => {
    freeChatEnabled = cbFreeChat.checked;
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
    if (document.getElementById('cb-reasoning').checked) {
        const v = selReasoning.value;
        if (v) c.reasoning_effort = v;
    }
    return c;
}

// ===== Отправка и обработка =====
async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    input.style.height = 'auto';
    btnSendChat.disabled = true;

    // Блокируем ввод на время запроса
    input.disabled = true;
    btnSendChat.disabled = true;

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                free_history: freeChatEnabled ? freeChatHistory : [],
                controlled_history: controlledChatHistory,
                constraints: collectConstraints(),
            }),
        });

        const data = await resp.json();

        if (data.error) {
            const errMsg = `Ошибка: ${escapeHtml(data.error)}`;
            addTurn(text, errMsg, errMsg, null, null, null, null, false);
            return;
        }

        // Сохраняем ответы в историю
        if (freeChatEnabled) {
            freeChatHistory.push({ role: 'user', content: text });
            freeChatHistory.push({ role: 'assistant', content: data.free_response.content });
        }
        controlledChatHistory.push({ role: 'user', content: text });
        controlledChatHistory.push({ role: 'assistant', content: data.controlled_response.content });

        // Рендерим строку
        addTurn(
            text,
            freeChatEnabled ? data.free_response.content : null,
            data.controlled_response.content,
            data.controlled_response.finish_reason,
            data.controlled_response.applied_params,
            freeChatEnabled ? data.free_response.usage : null,
            data.controlled_response.usage,
            freeChatEnabled,
            freeChatEnabled ? data.free_response.raw : null,
            data.controlled_response.raw,
            data.controlled_response.raw_request,
        );

    } catch (err) {
        const errMsg = `Ошибка сети: ${escapeHtml(err.message)}`;
        addTurn(text, errMsg, errMsg, null, null, null, null, false);
    } finally {
        input.disabled = false;
        btnSendChat.disabled = !input.value.trim();
        input.focus();
    }
}

// ===== Инициализация =====
window.addEventListener('load', () => {
    updateLayoutVars();
    initButtonVisibility();
    freeChatToggle.style.display = 'none';
    txtSysprompt.style.height = 'auto';
    txtSysprompt.style.height = txtSysprompt.scrollHeight + 'px';

    // Загружаем конфигурацию и заполняем UI
    loadConfig();
});

window.addEventListener('resize', updateLayoutVars);

btnSendChat.addEventListener('click', sendMessage);
