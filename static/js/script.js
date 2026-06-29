/**
 * script.js — ARIA Virtual Voice Assistant
 * Handles: Web Speech API, SpeechSynthesis, chat API, calculator, UI interactions
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
};

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

function formatMessageText(text) {
  // Format numbered lists as styled news list
  if (/^\d+\.\s/.test(text.trim())) {
    const lines = text.trim().split('\n');
    const header = lines[0].match(/^\d+\./) ? null : lines[0];
    const items = header ? lines.slice(1) : lines;
    const listItems = items
      .filter(l => l.trim())
      .map(l => `<li>${escapeHtml(l.replace(/^\d+\.\s/, ''))}</li>`)
      .join('');
    return (header ? `<p>${escapeHtml(header)}</p>` : '') + `<ul class="news-list">${listItems}</ul>`;
  }
  // Inline code
  let formatted = escapeHtml(text).replace(/`([^`]+)`/g, '<code>$1</code>');
  // Line breaks
  formatted = formatted.replace(/\n/g, '<br>');
  return formatted;
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
  // Strip HTML tags for speech
  const plainText = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  if (!plainText) return;

  state.synthesis.cancel();
  const utter = new SpeechSynthesisUtterance(plainText);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  utter.volume = 1.0;

  // Pick a good voice
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
    btn.textContent = state.speechEnabled ? '🔊' : '🔇';
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
    DOM.messageInput().placeholder = 'Type a message or press the mic to speak...';

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
    DOM.messageInput().placeholder = 'Type a message or press the mic to speak...';

    const errorMessages = {
      'no-speech':         'No speech detected. Try again.',
      'audio-capture':     'Microphone not accessible.',
      'not-allowed':       'Microphone permission denied.',
      'network':           'Network error during recognition.',
      'aborted':           null, // silently ignore
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
  msgDiv.innerHTML = `
    <div class="msg-avatar ${avatarClass}">${avatarIcon}</div>
    <div class="msg-content">
      <div class="msg-bubble">${formatMessageText(text)}${extraHtml}</div>
      <div class="msg-meta">
        <span>${isAi ? 'ARIA' : 'You'}</span>
        <span>·</span>
        <span>${time}</span>
      </div>
    </div>
  `;

  DOM.messagesInner().appendChild(msgDiv);
  scrollToBottom();

  // Record in history
  state.chatHistory.push({ role, text, time });
  saveChatHistory();

  return msgDiv;
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
// API Communication
// ──────────────────────────────────────────────────────────────────────────────

async function sendMessage(messageText) {
  const text = (messageText || DOM.messageInput().value).trim();
  if (!text || state.isLoading) return;

  state.isLoading = true;
  DOM.messageInput().value = '';
  autoResizeTextarea();
  DOM.sendBtn().disabled = true;

  // Show user message
  appendMessage('user', text);

  // Show typing indicator
  showTypingIndicator();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: state.sessionId }),
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

      // Handle URL action
      if (data.action === 'open_url' && data.url) {
        extraHtml = `
          <br>
          <a class="url-action-btn" href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer">
            🔗 Open Link
          </a>`;
        // Auto-open in new tab
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
    msgDiv.innerHTML = `
      <div class="msg-avatar ${role}">${avatarIcon}</div>
      <div class="msg-content">
        <div class="msg-bubble">${formatMessageText(text)}</div>
        <div class="msg-meta"><span>${role === 'ai' ? 'ARIA' : 'You'}</span></div>
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
  const userMessages = state.chatHistory.filter(m => m.role === 'user').slice(-8).reverse();
  
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
  // Clear backend session
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

  // Reset UI
  const inner = DOM.messagesInner();
  inner.innerHTML = '';

  // Show welcome screen again
  const ws = DOM.welcomeScreen();
  if (ws) {
    ws.classList.remove('hidden');
    ws.style.animation = '';
  }

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
    // Also remove from expression
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
    // Digit
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
    // Escape closes calculator
    if (e.key === 'Escape') {
      closeCalculator();
      closeSidebar();
    }

    // Ctrl+K focuses input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      DOM.messageInput().focus();
    }

    // Ctrl+/ toggles sidebar
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      toggleSidebar();
    }
  });

  // Calculator keyboard support
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
                      c.style.display = 'none'; // hide old chats
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
    if(ws) ws.style.display = 'none'; // Keep welcome screen hidden if there are chats
    showToast('Exited interview mode', 'info');
}

// ──────────────────────────────────────────────────────────────────────────────
// Event Listeners
// ──────────────────────────────────────────────────────────────────────────────

function setupEventListeners() {
  // Form submit
  DOM.inputForm().addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage();
  });

  // Textarea Enter key
  DOM.messageInput().addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Textarea resize
  DOM.messageInput().addEventListener('input', autoResizeTextarea);

  // Mic button
  DOM.micBtn().addEventListener('click', toggleMic);

  // Send button
  DOM.sendBtn().addEventListener('click', () => sendMessage());

  // Sidebar toggle
  DOM.sidebarToggle()?.addEventListener('click', toggleSidebar);

  // Overlay close
  DOM.sidebarOverlay()?.addEventListener('click', closeSidebar);

  // New chat
  DOM.newChatBtn()?.addEventListener('click', newChat);

  // Clear button (topbar)
  DOM.clearBtn()?.addEventListener('click', newChat);

  // Speech toggle
  DOM.speechToggle()?.addEventListener('click', toggleSpeech);

  // Calculator modal close
  DOM.calcClose()?.addEventListener('click', closeCalculator);
  DOM.calcModal()?.addEventListener('click', (e) => {
    if (e.target === DOM.calcModal()) closeCalculator();
  });

  // File Uploads
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

  // Voices may load asynchronously
  if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {};
  }

  // Focus input
  setTimeout(() => DOM.messageInput().focus(), 200);

  console.log('🤖 ARIA Virtual Voice Assistant initialized');
  console.log('🔑 Session ID:', state.sessionId);
}

// Expose globals for inline event handlers
window.handleSuggestion = handleSuggestion;
window.calcInput = calcInput;
window.openCalculator = openCalculator;
window.closeCalculator = closeCalculator;
window.loadHistoryItem = loadHistoryItem;
window.toggleSpeech = toggleSpeech;

document.addEventListener('DOMContentLoaded', init);
