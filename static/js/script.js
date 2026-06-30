/**
 * script.js — ARIA Virtual Voice Assistant
 * Handles: Web Speech API, SpeechSynthesis, chat API, calculator, UI interactions,
 *          Image Generation, Video Generation, Markdown rendering, Copy-to-clipboard
 */

'use strict';

// ──────────────────────────────────────────────────────────────────────────────
// State
// ──────────────────────────────────────────────────────────────────────────────

const state = {
  sessionId: generateSessionId(),
  isListening: false,
  isSpeaking: false,
  isLoading: false,
  speechEnabled: true,
  recognition: null,
  synthesis: window.speechSynthesis,
  chatHistory: [],           // [{role, text, time}]
  calcExpression: '',
  calcValue: '0',
  selectedLang: 'English',   // default response language
  isInterviewMode: false,
};

// ──────────────────────────────────────────────────────────────────────────────
// Language Selector
// ──────────────────────────────────────────────────────────────────────────────

const LANGUAGES = [
  { label: '🇺🇸 English',    value: 'English',    bcp47: 'en-US' },
  { label: '🇮🇳 Hindi',      value: 'Hindi',      bcp47: 'hi-IN' },
  { label: '🇮🇳 Tamil',      value: 'Tamil',      bcp47: 'ta-IN' },
  { label: '🇮🇳 Telugu',     value: 'Telugu',     bcp47: 'te-IN' },
  { label: '🇮🇳 Kannada',    value: 'Kannada',    bcp47: 'kn-IN' },
  { label: '🇮🇳 Malayalam',  value: 'Malayalam',  bcp47: 'ml-IN' },
  { label: '🇸🇦 Arabic',     value: 'Arabic',     bcp47: 'ar-SA' },
  { label: '🇫🇷 French',     value: 'French',     bcp47: 'fr-FR' },
  { label: '🇩🇪 German',     value: 'German',     bcp47: 'de-DE' },
  { label: '🇪🇸 Spanish',    value: 'Spanish',    bcp47: 'es-ES' },
  { label: '🇵🇹 Portuguese', value: 'Portuguese', bcp47: 'pt-PT' },
  { label: '🇯🇵 Japanese',   value: 'Japanese',   bcp47: 'ja-JP' },
  { label: '🇰🇷 Korean',     value: 'Korean',     bcp47: 'ko-KR' },
  { label: '🇨🇳 Chinese',    value: 'Chinese',    bcp47: 'zh-CN' },
  { label: '🇷🇺 Russian',    value: 'Russian',    bcp47: 'ru-RU' },
];

function buildLangOptions() {
  const container = document.getElementById('lang-options');
  if (!container) return;
  container.innerHTML = LANGUAGES.map(l => `
    <div class="lang-option" id="lang-opt-${l.value}"
      onclick="selectLang('${l.value}','${l.bcp47}')"
      style="padding:6px 12px;border-radius:8px;cursor:pointer;font-size:0.85rem;
             color:var(--text-primary);transition:background .15s;
             background:${ l.value === state.selectedLang ? 'var(--primary-subtle,rgba(124,58,237,.18))' : 'transparent' };"
      onmouseover="this.style.background='var(--bg-surface)'" onmouseout="this.style.background='${l.value === state.selectedLang ? 'var(--primary-subtle,rgba(124,58,237,.18))' : 'transparent'}'">
      ${l.label}${ l.value === state.selectedLang ? ' ✓' : '' }
    </div>`).join('');
}

function selectLang(value, bcp47) {
  state.selectedLang = value;
  if (state.recognition) state.recognition.lang = bcp47;
  updateLangBtn();
  buildLangOptions();
  document.getElementById('lang-custom').value = '';
  closeLangDropdown();
  showToast(`Language set to ${value}`, 'success', 2000);
}

function setCustomLang(value) {
  if (value.trim()) state.selectedLang = value.trim();
}

function updateLangBtn() {
  const btn = document.getElementById('lang-btn');
  if (!btn) return;
  const match = LANGUAGES.find(l => l.value === state.selectedLang);
  const flag = match ? match.label.split(' ')[0] : '🌐';
  btn.title = `Language: ${state.selectedLang}`;
  btn.innerHTML = `<span style="font-size:1.1rem;line-height:1">${flag}</span>`;
}

function toggleLangDropdown() {
  const dd = document.getElementById('lang-dropdown');
  if (!dd) return;
  const open = dd.style.display !== 'none';
  dd.style.display = open ? 'none' : 'block';
  if (!open) { buildLangOptions(); document.getElementById('lang-custom').value = ''; }
}

function closeLangDropdown() {
  const dd = document.getElementById('lang-dropdown');
  if (dd) dd.style.display = 'none';
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  const wrapper = document.getElementById('lang-selector-wrapper');
  if (wrapper && !wrapper.contains(e.target)) closeLangDropdown();
});

// ──────────────────────────────────────────────────────────────────────────────
// DOM References
// ──────────────────────────────────────────────────────────────────────────────

const DOM = {
  app:              () => document.getElementById('app'),
  sidebar:          () => document.getElementById('sidebar'),
  sidebarOverlay:   () => document.getElementById('sidebar-overlay'),
  sidebarToggle:    () => document.getElementById('sidebar-toggle'),
  chatMessages:     () => document.getElementById('chat-messages'),
  messagesInner:    () => document.getElementById('messages-inner'),
  welcomeScreen:    () => document.getElementById('welcome-screen'),
  inputForm:        () => document.getElementById('input-form'),
  messageInput:     () => document.getElementById('message-input'),
  micBtn:           () => document.getElementById('mic-btn'),
  sendBtn:          () => document.getElementById('send-btn'),
  voiceStatus:      () => document.getElementById('voice-status'),
  voiceStatusText:  () => document.getElementById('voice-status-text'),
  newChatBtn:       () => document.getElementById('new-chat-btn'),
  clearBtn:         () => document.getElementById('clear-btn'),
  speechToggle:     () => document.getElementById('speech-toggle'),
  chatHistoryList:  () => document.getElementById('chat-history-list'),
  calcModal:        () => document.getElementById('calculator-modal'),
  calcDisplay:      () => document.getElementById('calc-result'),
  calcExpression:   () => document.getElementById('calc-expression'),
  calcClose:        () => document.getElementById('calc-close'),
  toastContainer:   () => document.getElementById('toast-container'),
  statusBadge:      () => document.getElementById('status-text'),
  fileInput:        () => document.getElementById('file-input'),
  docInput:         () => document.getElementById('doc-input'),
  resumeInput:      () => document.getElementById('resume-input'),
  interviewBanner:  () => document.getElementById('interview-banner'),
  mockInterviewUi:  () => document.getElementById('mock-interview-ui'),
  interviewQuestion:() => document.getElementById('interview-current-question'),
  imageGenModal:    () => document.getElementById('image-gen-modal'),
  videoGenModal:    () => document.getElementById('video-gen-modal'),
  imageGenPrompt:   () => document.getElementById('image-gen-prompt'),
  videoGenPrompt:   () => document.getElementById('video-gen-prompt'),
  aiCoderModal:     () => document.getElementById('ai-coder-modal'),
  aiCoderPrompt:    () => document.getElementById('ai-coder-prompt'),
};

// ──────────────────────────────────────────────────────────────────────────────
// Utilities
// ──────────────────────────────────────────────────────────────────────────────

function generateSessionId() {
  return 'sess_' + Math.random().toString(36).slice(2, 11) + '_' + Date.now();
}

function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Enhanced markdown-style formatter with:
 * - Fenced code blocks with copy button
 * - Inline code
 * - Bold & italic
 * - Numbered and bulleted lists
 * - Line breaks
 */
function formatMessageText(text) {
  // ── Fenced code blocks ─────────────────────────────────
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const escaped = escapeHtml(code.trim());
    const langLabel = lang ? `<span class="code-lang-label">${escapeHtml(lang)}</span>` : '';
    return `<div class="code-block-wrapper">
      <div class="code-block-header">${langLabel}<button class="code-copy-btn" onclick="copyCode(this)" title="Copy code"><span class="material-symbols-rounded" style="font-size:14px">content_copy</span></button></div>
      <pre class="code-block"><code>${escaped}</code></pre>
    </div>`;
  });

  // ── Numbered list ───────────────────────────────────────
  if (/^\d+\.\s/m.test(text)) {
    const lines = text.split('\n');
    let inList = false;
    let result = '';
    for (const line of lines) {
      const match = line.match(/^(\d+)\.\s+(.*)/);
      if (match) {
        if (!inList) { result += '<ol class="msg-list">'; inList = true; }
        result += `<li>${formatInline(match[2])}</li>`;
      } else {
        if (inList) { result += '</ol>'; inList = false; }
        result += line ? `<p>${formatInline(line)}</p>` : '<br>';
      }
    }
    if (inList) result += '</ol>';
    return result;
  }

  // ── Bullet list ─────────────────────────────────────────
  if (/^[-*•]\s/m.test(text)) {
    const lines = text.split('\n');
    let inList = false;
    let result = '';
    for (const line of lines) {
      const match = line.match(/^[-*•]\s+(.*)/);
      if (match) {
        if (!inList) { result += '<ul class="msg-list">'; inList = true; }
        result += `<li>${formatInline(match[1])}</li>`;
      } else {
        if (inList) { result += '</ul>'; inList = false; }
        result += line ? `<p>${formatInline(line)}</p>` : '<br>';
      }
    }
    if (inList) result += '</ul>';
    return result;
  }

  // ── Default paragraph / inline formatting ────────────────
  return text.split('\n').map(line => line ? `<p>${formatInline(line)}</p>` : '<br>').join('');
}

function formatInline(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/_(.+?)_/g,       '<em>$1</em>')
    .replace(/`([^`]+)`/g,     '<code>$1</code>');
}

function copyCode(btn) {
  const code = btn.closest('.code-block-wrapper').querySelector('code');
  navigator.clipboard.writeText(code.textContent).then(() => {
    btn.innerHTML = '<span class="material-symbols-rounded" style="font-size:14px">check</span>';
    setTimeout(() => {
      btn.innerHTML = '<span class="material-symbols-rounded" style="font-size:14px">content_copy</span>';
    }, 2000);
  });
}

function copyMessage(btn) {
  const bubble = btn.closest('.msg-content').querySelector('.msg-bubble');
  const text = bubble ? bubble.innerText : '';
  navigator.clipboard.writeText(text).then(() => {
    btn.innerHTML = '<span class="material-symbols-rounded" style="font-size:14px">check</span>';
    showToast('Copied to clipboard!', 'success', 1500);
    setTimeout(() => {
      btn.innerHTML = '<span class="material-symbols-rounded" style="font-size:14px">content_copy</span>';
    }, 2000);
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// Toast Notifications
// ──────────────────────────────────────────────────────────────────────────────

function showToast(message, type = 'info', duration = 3500) {
  const icons = { info: '💡', success: '✅', error: '❌' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${escapeHtml(message)}</span>`;
  DOM.toastContainer().appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toast-out 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ──────────────────────────────────────────────────────────────────────────────
// Speech Synthesis (Text-to-Speech)
// ──────────────────────────────────────────────────────────────────────────────

function speak(text) {
  if (!state.speechEnabled || !state.synthesis) return;
  const plainText = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  if (!plainText) return;

  state.synthesis.cancel();
  const utter = new SpeechSynthesisUtterance(plainText);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  utter.volume = 1.0;

  const voices = state.synthesis.getVoices();
  const preferred = voices.find(v =>
    v.name.includes('Google') && v.lang.startsWith('en')
  ) || voices.find(v => v.lang.startsWith('en') && !v.name.includes('eSpeak'));
  if (preferred) utter.voice = preferred;

  utter.onstart = () => { state.isSpeaking = true; };
  utter.onend = () => { state.isSpeaking = false; };
  utter.onerror = () => { state.isSpeaking = false; };

  state.synthesis.speak(utter);
}

function toggleSpeech() {
  state.speechEnabled = !state.speechEnabled;
  const btn = DOM.speechToggle();
  if (btn) {
    btn.querySelector('span').textContent = state.speechEnabled ? 'volume_up' : 'volume_off';
    btn.title = state.speechEnabled ? 'Mute voice' : 'Unmute voice';
  }
  showToast(state.speechEnabled ? 'Voice output enabled' : 'Voice output muted', 'info', 2000);
  if (!state.speechEnabled) state.synthesis.cancel();
}

// ──────────────────────────────────────────────────────────────────────────────
// Speech Recognition (Voice Input)
// ──────────────────────────────────────────────────────────────────────────────

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    const micBtn = DOM.micBtn();
    if (micBtn) {
      micBtn.disabled = true;
      micBtn.title = 'Speech recognition not supported in this browser';
    }
    showToast('Speech recognition not supported. Use Chrome or Edge.', 'error', 5000);
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    state.isListening = true;
    DOM.micBtn().classList.add('listening');
    const vs = DOM.voiceStatus();
    if (vs) vs.classList.add('active');
    const vst = DOM.voiceStatusText();
    if (vst) vst.textContent = 'Listening...';
    DOM.messageInput().placeholder = '🎙️ Speak now...';
  };

  recognition.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += transcript;
      else interim += transcript;
    }
    DOM.messageInput().value = final || interim;
    autoResizeTextarea();
  };

  recognition.onend = () => {
    state.isListening = false;
    DOM.micBtn().classList.remove('listening');
    const vs = DOM.voiceStatus();
    if (vs) vs.classList.remove('active');
    DOM.messageInput().placeholder = "Ask ARIA anything, or try 'generate image of a sunset'...";

    const finalText = DOM.messageInput().value.trim();
    if (finalText) {
      setTimeout(() => sendMessage(finalText), 200);
    }
  };

  recognition.onerror = (event) => {
    state.isListening = false;
    DOM.micBtn().classList.remove('listening');
    const vs = DOM.voiceStatus();
    if (vs) vs.classList.remove('active');
    DOM.messageInput().placeholder = "Ask ARIA anything, or try 'generate image of a sunset'...";

    const errorMessages = {
      'no-speech':     'No speech detected. Try again.',
      'audio-capture': 'Microphone not accessible.',
      'not-allowed':   'Microphone permission denied.',
      'network':       'Network error during recognition.',
      'aborted':       null,
    };
    const msg = errorMessages[event.error];
    if (msg) showToast(msg, 'error');
  };

  state.recognition = recognition;
}

function toggleMic() {
  if (!state.recognition) {
    showToast('Speech recognition not available.', 'error');
    return;
  }
  if (state.isListening) {
    state.recognition.stop();
  } else {
    if (state.synthesis) state.synthesis.cancel();
    DOM.messageInput().value = '';
    state.recognition.start();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Chat UI
// ──────────────────────────────────────────────────────────────────────────────

function hideWelcomeScreen() {
  const ws = DOM.welcomeScreen();
  if (ws && !ws.classList.contains('hidden')) {
    ws.style.animation = 'toast-out 0.3s ease forwards';
    setTimeout(() => {
        ws.classList.add('hidden');
        ws.style.display = 'none';
    }, 300);
  }
}

function appendMessage(role, text, extraHtml = '') {
  hideWelcomeScreen();

  const time = formatTime();
  const isAi = role === 'ai';
  const avatarIcon = isAi ? '<span class="material-symbols-rounded">smart_toy</span>' : '<span class="material-symbols-rounded">person</span>';
  const avatarClass = isAi ? 'ai' : 'user';

  const msgDiv = document.createElement('div');
  if (state.isInterviewMode) {
      msgDiv.classList.add('interview-mode-msg');
  }
  msgDiv.className = `message ${role}`;

  const copyBtn = isAi ? `
    <button class="msg-copy-btn" onclick="copyMessage(this)" title="Copy message" aria-label="Copy message">
      <span class="material-symbols-rounded" style="font-size:14px">content_copy</span>
    </button>` : '';

  msgDiv.innerHTML = `
    <div class="msg-avatar ${avatarClass}">${avatarIcon}</div>
    <div class="msg-content">
      <div class="msg-bubble">${formatMessageText(text)}${extraHtml}</div>
      <div class="msg-meta">
        <span>${isAi ? 'ARIA' : 'You'}</span>
        <span>·</span>
        <span>${time}</span>
        ${copyBtn}
      </div>
    </div>
  `;

  DOM.messagesInner().appendChild(msgDiv);
  scrollToBottom();

  state.chatHistory.push({ role, text, time });
  saveChatHistory();

  return msgDiv;
}

/** Append a generated image result bubble */
function appendImageMessage(prompt, imageUrl) {
  hideWelcomeScreen();
  const time = formatTime();
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message ai';
  msgDiv.innerHTML = `
    <div class="msg-avatar ai"><span class="material-symbols-rounded">auto_awesome</span></div>
    <div class="msg-content">
      <div class="msg-bubble gen-image-bubble">
        <p class="gen-caption">🖼️ Generated: <em>${escapeHtml(prompt)}</em></p>
        <img src="${imageUrl}" alt="${escapeHtml(prompt)}" class="gen-image" loading="lazy" />
        <div class="gen-image-actions">
          <a href="${imageUrl}" download="aria-generated.png" class="url-action-btn">
            <span class="material-symbols-rounded" style="font-size:14px">download</span> Download
          </a>
        </div>
      </div>
      <div class="msg-meta"><span>ARIA · Image Gen</span><span>·</span><span>${time}</span></div>
    </div>
  `;
  DOM.messagesInner().appendChild(msgDiv);
  scrollToBottom();
  state.chatHistory.push({ role: 'ai', text: `[Generated image: ${prompt}]`, time });
  saveChatHistory();
}

/** Append a generated video result bubble */
function appendVideoMessage(prompt, videoUrl) {
  hideWelcomeScreen();
  const time = formatTime();
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message ai';
  msgDiv.innerHTML = `
    <div class="msg-avatar ai"><span class="material-symbols-rounded">videocam</span></div>
    <div class="msg-content">
      <div class="msg-bubble gen-video-bubble">
        <p class="gen-caption">🎬 Generated: <em>${escapeHtml(prompt)}</em></p>
        <video src="${videoUrl}" class="gen-video" controls autoplay muted loop></video>
        <div class="gen-image-actions">
          <a href="${videoUrl}" download="aria-generated.mp4" class="url-action-btn">
            <span class="material-symbols-rounded" style="font-size:14px">download</span> Download
          </a>
        </div>
      </div>
      <div class="msg-meta"><span>ARIA · Video Gen</span><span>·</span><span>${time}</span></div>
    </div>
  `;
  DOM.messagesInner().appendChild(msgDiv);
  scrollToBottom();
  state.chatHistory.push({ role: 'ai', text: `[Generated video: ${prompt}]`, time });
  saveChatHistory();
}

function showTypingIndicator() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'typing-indicator';
  typingDiv.id = 'typing-indicator';
  typingDiv.innerHTML = `
    <div class="msg-avatar ai"><span class="material-symbols-rounded">smart_toy</span></div>
    <div class="typing-bubble">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  DOM.messagesInner().appendChild(typingDiv);
  scrollToBottom();
}

function removeTypingIndicator() {
  const indicator = document.getElementById('typing-indicator');
  if (indicator) indicator.remove();
}

function scrollToBottom() {
  const container = DOM.chatMessages();
  setTimeout(() => {
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }, 50);
}

// ──────────────────────────────────────────────────────────────────────────────
// Image Generation Prompts (natural language detection)
// ──────────────────────────────────────────────────────────────────────────────

const IMAGE_TRIGGERS = [
  /^generate (?:an? )?image (?:of|about|showing|depicting|with)?\s*(.+)/i,
  /^create (?:an? )?image (?:of|about|showing)?\s*(.+)/i,
  /^draw (?:me )?(?:an? )?\s*(.+)/i,
  /^make (?:an? )?image (?:of|about)?\s*(.+)/i,
  /^show me (?:an? )?(?:picture|image|photo) (?:of|about)\s*(.+)/i,
  /^picture of\s*(.+)/i,
  /^paint\s+(.+)/i,
];

const VIDEO_TRIGGERS = [
  /^generate (?:a )?video (?:of|about|showing)?\s*(.+)/i,
  /^create (?:a )?video (?:of|about)?\s*(.+)/i,
  /^make (?:a )?video (?:of|about)?\s*(.+)/i,
  /^animate\s+(.+)/i,
];

function detectMediaIntent(text) {
  for (const rx of IMAGE_TRIGGERS) {
    const m = text.match(rx);
    if (m) return { type: 'image', prompt: m[1].trim() };
  }
  for (const rx of VIDEO_TRIGGERS) {
    const m = text.match(rx);
    if (m) return { type: 'video', prompt: m[1].trim() };
  }
  return null;
}

// ──────────────────────────────────────────────────────────────────────────────
// API Communication
// ──────────────────────────────────────────────────────────────────────────────

async function sendMessage(messageText) {
  const text = (messageText || DOM.messageInput().value).trim();
  if (!text || state.isLoading) return;

  // ── Check for image/video intent ──────────────────────────────────────────
  const mediaIntent = detectMediaIntent(text);
  if (mediaIntent) {
    DOM.messageInput().value = '';
    autoResizeTextarea();
    appendMessage('user', text);
    if (mediaIntent.type === 'image') {
      await generateImage(mediaIntent.prompt);
    } else {
      await generateVideo(mediaIntent.prompt);
    }
    return;
  }

  state.isLoading = true;
  DOM.messageInput().value = '';
  autoResizeTextarea();
  DOM.sendBtn().disabled = true;

  appendMessage('user', text);
  showTypingIndicator();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: state.sessionId,
        lang: state.selectedLang,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    removeTypingIndicator();

    if (data.error && !data.text) {
      appendMessage('ai', '⚠️ ' + data.error);
      showToast(data.error, 'error');
    } else {
      const responseText = data.text || 'I received your message.';
      let extraHtml = '';

      if (data.action === 'open_url' && data.url) {
        extraHtml = `
          <br>
          <a class="url-action-btn" href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer">
            🔗 Open Link
          </a>`;
        setTimeout(() => window.open(data.url, '_blank', 'noopener,noreferrer'), 300);
      } else if (data.action === 'open_calculator') {
        extraHtml = '';
        setTimeout(() => openCalculator(), 300);
      }

      appendMessage('ai', responseText, extraHtml);
      speak(responseText);
      if (state.isInterviewMode) {
          DOM.interviewQuestion().textContent = responseText;
      }
    }

  } catch (err) {
    removeTypingIndicator();
    console.error('Chat API error:', err);
    const errMsg = 'Sorry, I had trouble connecting to the server. Please try again.';
    appendMessage('ai', errMsg);
    showToast('Connection error. Is the server running?', 'error');
    speak(errMsg);
  } finally {
    state.isLoading = false;
    DOM.sendBtn().disabled = false;
    DOM.messageInput().focus();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Image Generation
// ──────────────────────────────────────────────────────────────────────────────

async function generateImage(prompt) {
  if (!prompt || state.isLoading) return;
  state.isLoading = true;
  DOM.sendBtn().disabled = true;
  showTypingIndicator();

  // Update typing indicator to show image gen context
  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    const bubble = indicator.querySelector('.typing-bubble');
    if (bubble) bubble.innerHTML += '<span style="margin-left:8px;font-size:0.75rem;color:var(--text-muted)">Generating image...</span>';
  }

  try {
    const response = await fetch('/api/generate/image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();
    removeTypingIndicator();

    if (data.image_url) {
      appendImageMessage(prompt, data.image_url);
    } else if (data.text) {
      appendMessage('ai', data.text);
    } else {
      appendMessage('ai', '⚠️ ' + (data.error || 'Image generation failed.'));
    }
  } catch (err) {
    removeTypingIndicator();
    appendMessage('ai', '⚠️ Image generation failed. Please try again.');
    showToast('Image generation error.', 'error');
  } finally {
    state.isLoading = false;
    DOM.sendBtn().disabled = false;
    DOM.messageInput().focus();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Video Generation
// ──────────────────────────────────────────────────────────────────────────────

async function generateVideo(prompt) {
  if (!prompt || state.isLoading) return;
  state.isLoading = true;
  DOM.sendBtn().disabled = true;
  showTypingIndicator();

  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    const bubble = indicator.querySelector('.typing-bubble');
    if (bubble) bubble.innerHTML += '<span style="margin-left:8px;font-size:0.75rem;color:var(--text-muted)">Generating video... (may take up to 60s)</span>';
  }

  showToast('Generating video — this may take a moment...', 'info', 8000);

  try {
    const response = await fetch('/api/generate/video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();
    removeTypingIndicator();

    if (data.video_url) {
      appendVideoMessage(prompt, data.video_url);
    } else if (data.text) {
      appendMessage('ai', data.text);
    } else {
      appendMessage('ai', '⚠️ ' + (data.error || 'Video generation failed.'));
    }
  } catch (err) {
    removeTypingIndicator();
    appendMessage('ai', '⚠️ Video generation failed. Please try again.');
    showToast('Video generation error.', 'error');
  } finally {
    state.isLoading = false;
    DOM.sendBtn().disabled = false;
    DOM.messageInput().focus();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// AI Coder Modal
// ──────────────────────────────────────────────────────────────────────────────

function openAiCoderModal() {
  const modal = DOM.aiCoderModal();
  if (modal) {
    modal.classList.add('open');
    setTimeout(() => DOM.aiCoderPrompt() && DOM.aiCoderPrompt().focus(), 100);
  }
}

function closeAiCoderModal() {
  const modal = DOM.aiCoderModal();
  if (modal) modal.classList.remove('open');
}

function setCoderPrompt(text) {
  const ta = DOM.aiCoderPrompt();
  if (ta) ta.value = text;
}

function submitAiCoder() {
  const prompt = (DOM.aiCoderPrompt()?.value || '').trim();
  if (!prompt) { showToast('Please enter code or a prompt.', 'error', 2000); return; }

  closeAiCoderModal();
  // Instruct the assistant to act as a coding assistant explicitly
  const codingPrompt = `You are an expert AI Coding Assistant. Please handle the following request:\n\n${prompt}`;
  
  DOM.messageInput().value = codingPrompt;
  autoResizeTextarea();
  sendMessage(codingPrompt);
  
  if (DOM.aiCoderPrompt()) DOM.aiCoderPrompt().value = '';
}

// ──────────────────────────────────────────────────────────────────────────────
// Image Gen Modal
// ──────────────────────────────────────────────────────────────────────────────

function openImageGenModal() {
  const modal = DOM.imageGenModal();
  if (modal) {
    modal.classList.add('open');
    setTimeout(() => DOM.imageGenPrompt() && DOM.imageGenPrompt().focus(), 100);
  }
}

function closeImageGenModal() {
  const modal = DOM.imageGenModal();
  if (modal) modal.classList.remove('open');
}

function setImagePrompt(text) {
  const ta = DOM.imageGenPrompt();
  if (ta) ta.value = text;
}

async function submitImageGen() {
  const prompt = (DOM.imageGenPrompt()?.value || '').trim();
  if (!prompt) { showToast('Please enter a prompt.', 'error', 2000); return; }

  closeImageGenModal();
  appendMessage('user', `Generate image: ${prompt}`);
  await generateImage(prompt);
  if (DOM.imageGenPrompt()) DOM.imageGenPrompt().value = '';
}

// ──────────────────────────────────────────────────────────────────────────────
// Video Gen Modal
// ──────────────────────────────────────────────────────────────────────────────

function openVideoGenModal() {
  const modal = DOM.videoGenModal();
  if (modal) {
    modal.classList.add('open');
    setTimeout(() => DOM.videoGenPrompt() && DOM.videoGenPrompt().focus(), 100);
  }
}

function closeVideoGenModal() {
  const modal = DOM.videoGenModal();
  if (modal) modal.classList.remove('open');
}

function setVideoPrompt(text) {
  const ta = DOM.videoGenPrompt();
  if (ta) ta.value = text;
}

async function submitVideoGen() {
  const prompt = (DOM.videoGenPrompt()?.value || '').trim();
  if (!prompt) { showToast('Please enter a prompt.', 'error', 2000); return; }

  closeVideoGenModal();
  appendMessage('user', `Generate video: ${prompt}`);
  await generateVideo(prompt);
  if (DOM.videoGenPrompt()) DOM.videoGenPrompt().value = '';
}

// ──────────────────────────────────────────────────────────────────────────────
// Chat History (Local Storage)
// ──────────────────────────────────────────────────────────────────────────────

function saveChatHistory() {
  try {
    localStorage.setItem('aria_history', JSON.stringify(state.chatHistory.slice(-100)));
    updateHistoryPanel();
  } catch (_) {}
}

function loadChatHistory() {
  try {
    const stored = localStorage.getItem('aria_history');
    if (stored) {
      state.chatHistory = JSON.parse(stored);
      restoreChatFromHistory();
    }
  } catch (_) {}
}

function restoreChatFromHistory() {
  if (!state.chatHistory.length) return;
  hideWelcomeScreen();
  state.chatHistory.forEach(({ role, text }) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    const avatarIcon = role === 'ai' ? '<span class="material-symbols-rounded">smart_toy</span>' : '<span class="material-symbols-rounded">person</span>';
    const isAi = role === 'ai';
    const copyBtn = isAi ? `
      <button class="msg-copy-btn" onclick="copyMessage(this)" title="Copy message">
        <span class="material-symbols-rounded" style="font-size:14px">content_copy</span>
      </button>` : '';
    msgDiv.innerHTML = `
      <div class="msg-avatar ${role}">${avatarIcon}</div>
      <div class="msg-content">
        <div class="msg-bubble">${formatMessageText(text)}</div>
        <div class="msg-meta"><span>${role === 'ai' ? 'ARIA' : 'You'}</span>${copyBtn}</div>
      </div>
    `;
    DOM.messagesInner().appendChild(msgDiv);
  });
  scrollToBottom();
  updateHistoryPanel();
}

function updateHistoryPanel() {
  const list = DOM.chatHistoryList();
  if (!list) return;
  const userMessages = state.chatHistory.filter(m => m.role === 'user').slice(-10).reverse();

  window._currentUserMessages = userMessages;

  list.innerHTML = userMessages.length === 0
    ? '<div style="padding:8px 12px;font-size:0.75rem;color:var(--text-muted)">No history yet</div>'
    : userMessages.map((m, idx) => `
        <div class="history-item" onclick="loadHistoryItem(window._currentUserMessages[${idx}].text)">
          <span class="hist-icon">💬</span>
          <span style="flex: 1; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(m.text.slice(0, 45))}${m.text.length > 45 ? '…' : ''}</span>
          <span class="material-symbols-rounded delete-hist-btn" onclick="deleteHistoryItem(event, ${idx})" title="Delete chat">delete</span>
        </div>
      `).join('');
}

// Alias for backwards compat
const renderChatHistory = updateHistoryPanel;

function deleteHistoryItem(event, index) {
  event.stopPropagation();
  if (!window._currentUserMessages || !window._currentUserMessages[index]) return;
  const item = window._currentUserMessages[index];

  const originalIndex = state.chatHistory.findIndex(m => m.text === item.text && m.time === item.time);
  if (originalIndex !== -1) {
    if (originalIndex + 1 < state.chatHistory.length && state.chatHistory[originalIndex + 1].role === 'ai') {
      state.chatHistory.splice(originalIndex, 2);
    } else {
      state.chatHistory.splice(originalIndex, 1);
    }
  }

  saveChatHistory();
  renderChatHistory();
}

function loadHistoryItem(text) {
  DOM.messageInput().value = text;
  autoResizeTextarea();
  DOM.messageInput().focus();
  closeSidebar();
}

async function newChat() {
  try {
    await fetch('/api/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId }),
    });
  } catch (_) {}

  state.sessionId = generateSessionId();
  state.chatHistory = [];
  localStorage.removeItem('aria_history');

  const inner = DOM.messagesInner();
  inner.innerHTML = '';

  // Re-add welcome screen skeleton
  inner.innerHTML = `
    <div class="welcome-screen" id="welcome-screen" aria-label="Welcome">
      <div class="welcome-avatar">
        <div class="avatar-pulse" aria-hidden="true"></div>
        <div class="avatar-ring" aria-hidden="true"></div>
        <div class="avatar-image" aria-hidden="true"><span class="material-symbols-rounded" style="font-size: 48px; color: var(--primary-light);">smart_toy</span></div>
      </div>
      <h2>Hi, I'm ARIA</h2>
      <p>Start a new conversation below!</p>
    </div>
    <div id="mock-interview-ui" style="display: none;" class="glass-panel interview-panel">
      <div class="interview-avatar">
        <div class="avatar-pulse"></div>
        <span class="material-symbols-rounded ai-avatar-icon" style="font-size: 64px; color: #fff;">smart_toy</span>
      </div>
      <div class="interview-text-content">
        <h3 id="interview-question-heading">ARIA - Interviewer</h3>
        <p id="interview-current-question">Please introduce yourself.</p>
      </div>
    </div>
  `;

  updateHistoryPanel();
  showToast('New conversation started', 'success', 2000);
}

// ──────────────────────────────────────────────────────────────────────────────
// Calculator
// ──────────────────────────────────────────────────────────────────────────────

function openCalculator() {
  DOM.calcModal().classList.add('open');
  state.calcExpression = '';
  state.calcValue = '0';
  updateCalcDisplay();
}

function closeCalculator() {
  DOM.calcModal().classList.remove('open');
}

function updateCalcDisplay() {
  DOM.calcDisplay().textContent = state.calcValue;
  DOM.calcExpression().textContent = state.calcExpression;
}

function calcInput(val) {
  const operators = ['+', '-', '×', '÷', '%'];

  if (val === 'C') {
    state.calcExpression = '';
    state.calcValue = '0';
  } else if (val === '⌫') {
    if (state.calcValue.length > 1) {
      state.calcValue = state.calcValue.slice(0, -1);
    } else {
      state.calcValue = '0';
    }
    if (state.calcExpression.length > 0) {
      state.calcExpression = state.calcExpression.slice(0, -1);
    }
  } else if (val === '=') {
    try {
      const expr = state.calcExpression
        .replace(/×/g, '*')
        .replace(/÷/g, '/')
        .replace(/,/g, '');
      if (!expr) return;
      // eslint-disable-next-line no-new-func
      const result = Function('"use strict"; return (' + expr + ')')();
      if (!isFinite(result)) throw new Error('Invalid');
      state.calcValue = String(parseFloat(result.toFixed(10)));
      state.calcExpression = state.calcValue;
    } catch {
      state.calcValue = 'Error';
      state.calcExpression = '';
    }
  } else if (val === '+/-') {
    if (state.calcValue !== '0') {
      state.calcValue = state.calcValue.startsWith('-')
        ? state.calcValue.slice(1)
        : '-' + state.calcValue;
    }
  } else if (operators.includes(val)) {
    state.calcExpression += state.calcValue + val;
    state.calcValue = '';
  } else if (val === '.') {
    if (!state.calcValue.includes('.')) {
      state.calcValue = (state.calcValue || '0') + '.';
      state.calcExpression += '.';
    }
  } else {
    if (state.calcValue === '0' || state.calcValue === 'Error') {
      state.calcValue = val;
    } else {
      state.calcValue += val;
    }
    state.calcExpression += val;
  }

  updateCalcDisplay();
}

// ──────────────────────────────────────────────────────────────────────────────
// Sidebar
// ──────────────────────────────────────────────────────────────────────────────

function toggleSidebar() {
  const sidebar = DOM.sidebar();
  const overlay = DOM.sidebarOverlay();
  const isMobile = window.innerWidth <= 768;

  if (isMobile) {
    sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('visible');
  } else {
    sidebar.classList.toggle('collapsed');
  }
}

function closeSidebar() {
  const sidebar = DOM.sidebar();
  const overlay = DOM.sidebarOverlay();
  sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('visible');
}

// ──────────────────────────────────────────────────────────────────────────────
// Textarea Auto-resize
// ──────────────────────────────────────────────────────────────────────────────

function autoResizeTextarea() {
  const ta = DOM.messageInput();
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 140) + 'px';
}

// ──────────────────────────────────────────────────────────────────────────────
// Suggestion Chips
// ──────────────────────────────────────────────────────────────────────────────

function handleSuggestion(text) {
  DOM.messageInput().value = text;
  autoResizeTextarea();
  sendMessage(text);
}

// ──────────────────────────────────────────────────────────────────────────────
// Health Check
// ──────────────────────────────────────────────────────────────────────────────

async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return;
    const data = await res.json();
    const badge = DOM.statusBadge();
    if (badge) {
      const backend = data.ai_backend || 'fallback';
      badge.textContent = `ARIA Online · ${backend.charAt(0).toUpperCase() + backend.slice(1)}`;
    }
  } catch (_) {
    const badge = DOM.statusBadge();
    if (badge) badge.textContent = 'ARIA · Offline';
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Keyboard Shortcuts
// ──────────────────────────────────────────────────────────────────────────────

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeCalculator();
      closeSidebar();
      closeImageGenModal();
      closeVideoGenModal();
      closeAiCoderModal();
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      DOM.messageInput().focus();
    }

    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      toggleSidebar();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (!DOM.calcModal().classList.contains('open')) return;
    const keyMap = {
      '0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',
      '.':'.', '+':'+', '-':'-', '*':'×', '/':'÷', '%':'%',
      'Enter':'=', '=':'=', 'Backspace':'⌫', 'Delete':'C',
    };
    const mapped = keyMap[e.key];
    if (mapped) { e.preventDefault(); calcInput(mapped); }
  });

  // Close gen modals on backdrop click
  document.getElementById('image-gen-modal')?.addEventListener('click', (e) => {
    if (e.target === document.getElementById('image-gen-modal')) closeImageGenModal();
  });
  document.getElementById('video-gen-modal')?.addEventListener('click', (e) => {
    if (e.target === document.getElementById('video-gen-modal')) closeVideoGenModal();
  });
  document.getElementById('ai-coder-modal')?.addEventListener('click', (e) => {
    if (e.target === document.getElementById('ai-coder-modal')) closeAiCoderModal();
  });

  // Submit on Ctrl+Enter in textarea
  document.getElementById('image-gen-prompt')?.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitImageGen(); }
  });
  document.getElementById('video-gen-prompt')?.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitVideoGen(); }
  });
  document.getElementById('ai-coder-prompt')?.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); submitAiCoder(); }
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// File Upload & Interview Handlers
// ──────────────────────────────────────────────────────────────────────────────

async function handleFileUpload(file, endpoint) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', state.sessionId);

  state.isLoading = true;
  DOM.sendBtn().disabled = true;
  appendMessage('user', `[Uploaded file: ${file.name}]`);
  showTypingIndicator();

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    const data = await res.json();
    removeTypingIndicator();

    if (data.error) {
        appendMessage('ai', '⚠️ ' + data.error);
        showToast(data.error, 'error');
    } else {
        appendMessage('ai', data.text || 'File processed.');
        speak(data.text);
    }
  } catch(err) {
      removeTypingIndicator();
      appendMessage('ai', 'Error uploading file.');
  } finally {
      state.isLoading = false;
      DOM.sendBtn().disabled = false;
  }
}

async function startInterviewWithResume(file) {
  if (!file) return;
  showToast('Parsing resume and starting interview...', 'info');

  const reader = new FileReader();
  reader.onload = async (e) => {
      const text = e.target.result;
      state.isLoading = true;
      try {
          const res = await fetch('/api/interview/start', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({resume_text: text, session_id: state.sessionId})
          });
          const data = await res.json();
          if (data.error) {
              showToast(data.error, 'error');
          } else {
              state.isInterviewMode = true;
              DOM.interviewBanner().style.display = 'flex';
              DOM.mockInterviewUi().style.display = 'flex';
              Array.from(DOM.messagesInner().children).forEach(c => {
                  if (c.id !== 'mock-interview-ui' && c.id !== 'welcome-screen') {
                      c.style.display = 'none';
                  }
              });
              hideWelcomeScreen();

              DOM.interviewQuestion().textContent = data.text;
              appendMessage('ai', data.text);
              speak(data.text);
          }
      } catch(err) {
          showToast('Failed to start interview', 'error');
      } finally {
          state.isLoading = false;
      }
  };
  reader.readAsText(file);
}

window.exitInterview = async function() {
    try {
        await fetch('/api/interview/exit', {method: 'POST'});
    } catch(e) {}
    state.isInterviewMode = false;
    DOM.interviewBanner().style.display = 'none';
    DOM.mockInterviewUi().style.display = 'none';
    Array.from(DOM.messagesInner().children).forEach(c => {
        if (c.id !== 'mock-interview-ui') {
            c.style.display = 'flex';
        }
    });
    const ws = DOM.welcomeScreen();
    if(ws) ws.style.display = 'none';
    showToast('Exited interview mode', 'info');
};

// ──────────────────────────────────────────────────────────────────────────────
// Event Listeners
// ──────────────────────────────────────────────────────────────────────────────

function setupEventListeners() {
  DOM.inputForm().addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage();
  });

  DOM.messageInput().addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  DOM.messageInput().addEventListener('input', autoResizeTextarea);

  DOM.micBtn().addEventListener('click', toggleMic);
  DOM.sendBtn().addEventListener('click', () => sendMessage());

  DOM.sidebarToggle()?.addEventListener('click', toggleSidebar);
  DOM.sidebarOverlay()?.addEventListener('click', closeSidebar);

  DOM.newChatBtn()?.addEventListener('click', newChat);
  DOM.clearBtn()?.addEventListener('click', newChat);

  DOM.speechToggle()?.addEventListener('click', toggleSpeech);

  DOM.calcClose()?.addEventListener('click', closeCalculator);
  DOM.calcModal()?.addEventListener('click', (e) => {
    if (e.target === DOM.calcModal()) closeCalculator();
  });

  DOM.fileInput()?.addEventListener('change', (e) => handleFileUpload(e.target.files[0], '/api/upload/image'));
  DOM.docInput()?.addEventListener('change', (e) => handleFileUpload(e.target.files[0], '/api/upload/document'));
  DOM.resumeInput()?.addEventListener('change', (e) => startInterviewWithResume(e.target.files[0]));
}

// ──────────────────────────────────────────────────────────────────────────────
// Init
// ──────────────────────────────────────────────────────────────────────────────

function init() {
  initSpeechRecognition();
  setupEventListeners();
  setupKeyboardShortcuts();
  loadChatHistory();
  checkHealth();
  buildLangOptions();
  updateLangBtn();

  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {};
  }

  setTimeout(() => DOM.messageInput().focus(), 200);

  console.log('🤖 ARIA Virtual Voice Assistant initialized');
  console.log('🔑 Session ID:', state.sessionId);
}

// Expose globals for inline event handlers
window.handleSuggestion   = handleSuggestion;
window.calcInput          = calcInput;
window.openCalculator     = openCalculator;
window.closeCalculator    = closeCalculator;
window.loadHistoryItem    = loadHistoryItem;
window.deleteHistoryItem  = deleteHistoryItem;
window.toggleSpeech       = toggleSpeech;
window.toggleLangDropdown = toggleLangDropdown;
window.closeLangDropdown  = closeLangDropdown;
window.selectLang         = selectLang;
window.setCustomLang      = setCustomLang;
window.exitInterview      = exitInterview;
window.openImageGenModal  = openImageGenModal;
window.closeImageGenModal = closeImageGenModal;
window.setImagePrompt     = setImagePrompt;
window.submitImageGen     = submitImageGen;
window.openVideoGenModal  = openVideoGenModal;
window.closeVideoGenModal = closeVideoGenModal;
window.setVideoPrompt     = setVideoPrompt;
window.submitVideoGen     = submitVideoGen;
window.openAiCoderModal   = openAiCoderModal;
window.closeAiCoderModal  = closeAiCoderModal;
window.setCoderPrompt     = setCoderPrompt;
window.submitAiCoder      = submitAiCoder;
window.generateImage      = generateImage;
window.generateVideo      = generateVideo;
window.copyCode           = copyCode;
window.copyMessage        = copyMessage;
window.newChat            = newChat;
window.toggleMic          = toggleMic;
window.toggleSidebar      = toggleSidebar;

document.addEventListener('DOMContentLoaded', init);
