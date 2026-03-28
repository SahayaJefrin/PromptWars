// ─── STATE ───────────────────────────────────────────────
let recognition = null;
let isListening  = false;
let currentLang  = 'en';
let currentTranscript = '';

// ─── i18n ─────────────────────────────────────────────────
const i18n = {
  en: {
    describe:   'Describe the Emergency',
    placeholder:'Press 🎙 and speak what\'s happening...',
    typehere:   'e.g. My uncle collapsed, not breathing...',
    or:         'or type below',
    analyze:    '⚡ Get Emergency Plan',
    analyzing:  'ANALYZING EMERGENCY...',
    idleTitle:  'Ready to respond',
    idleSub:    'Speak or type what\'s happening. FirstVoice tells you exactly what to do.',
    steps:      'Action Steps',
    donot:      'DO NOT',
    dispatch:   '📡 EMERGENCY DISPATCH BRIEF',
    tts:        '🔊 Read aloud',
    listening:  'Listening... speak now',
    speechErr:  'Speech recognition not available. Please type instead.',
    noInput:    'Please speak or type the emergency situation.',
  },
  hi: {
    describe:   'आपातकाल का वर्णन करें',
    placeholder:'🎙 दबाएं और बोलें क्या हो रहा है...',
    typehere:   'उदा. मेरे चाचा गिर गए, सांस नहीं ले रहे...',
    or:         'या नीचे टाइप करें',
    analyze:    '⚡ आपातकालीन योजना प्राप्त करें',
    analyzing:  'आपातकाल विश्लेषण हो रहा है...',
    idleTitle:  'प्रतिक्रिया के लिए तैयार',
    idleSub:    'बोलें या टाइप करें। FirstVoice आपको बताएगा क्या करना है।',
    steps:      'कदम',
    donot:      'यह मत करें',
    dispatch:   '📡 एम्बुलेंस को बताएं',
    tts:        '🔊 ज़ोर से पढ़ें',
    listening:  'सुन रहा हूं... अभी बोलें',
    speechErr:  'वॉइस उपलब्ध नहीं। कृपया टाइप करें।',
    noInput:    'कृपया आपातकाल बताएं।',
  },
  kn: {
    describe:   'ತುರ್ತು ಪರಿಸ್ಥಿತಿ ವಿವರಿಸಿ',
    placeholder:'🎙 ಒತ್ತಿ ಮತ್ತು ಏನಾಗುತ್ತಿದೆ ಎಂದು ಹೇಳಿ...',
    typehere:   'ಉದಾ. ನನ್ನ ಅಂಕಲ್ ಬಿದ್ದರು, ಉಸಿರಾಡುತ್ತಿಲ್ಲ...',
    or:         'ಅಥವಾ ಕೆಳಗೆ ಟೈಪ್ ಮಾಡಿ',
    analyze:    '⚡ ತುರ್ತು ಯೋಜನೆ ಪಡೆಯಿರಿ',
    analyzing:  'ತುರ್ತು ಪರಿಸ್ಥಿತಿ ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...',
    idleTitle:  'ಪ್ರತಿಕ್ರಿಯಿಸಲು ಸಿದ್ಧ',
    idleSub:    'ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ. FirstVoice ನಿಮಗೆ ಏನು ಮಾಡಬೇಕೆಂದು ತಿಳಿಸುತ್ತದೆ.',
    steps:      'ಹಂತಗಳು',
    donot:      'ಮಾಡಬೇಡಿ',
    dispatch:   '📡 ತುರ್ತು ಸೇವೆ ಸಾರಾಂಶ',
    tts:        '🔊 ಜೋರಾಗಿ ಓದಿ',
    listening:  'ಆಲಿಸುತ್ತಿದ್ದೇನೆ...',
    speechErr:  'ಧ್ವನಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಟೈಪ್ ಮಾಡಿ.',
    noInput:    'ದಯವಿಟ್ಟು ತುರ್ತು ಪರಿಸ್ಥಿತಿ ತಿಳಿಸಿ.',
  },
  ta: {
    describe:   'அவசரநிலையை விவரிக்கவும்',
    placeholder:'🎙 அழுத்தி என்ன நடக்கிறது என்று சொல்லுங்கள்...',
    typehere:   'எ.கா. என் மாமா விழுந்தார், மூச்சு இல்லை...',
    or:         'அல்லது கீழே தட்டச்சு செய்யுங்கள்',
    analyze:    '⚡ அவசர திட்டம் பெறுங்கள்',
    analyzing:  'அவசரநிலை பகுப்பாய்வு...',
    idleTitle:  'பதிலளிக்க தயார்',
    idleSub:    'பேசுங்கள் அல்லது தட்டச்சு செய்யுங்கள். FirstVoice என்ன செய்வதெனக் கூறும்.',
    steps:      'நடவடிக்கை படிகள்',
    donot:      'செய்யாதீர்கள்',
    dispatch:   '📡 அவசர சுருக்கம்',
    tts:        '🔊 சத்தமாக படிக்கவும்',
    listening:  'கேட்கிறேன்...',
    speechErr:  'குரல் இல்லை. தட்டச்சு செய்யுங்கள்.',
    noInput:    'அவசரநிலையை தெரிவிக்கவும்.',
  },
  te: {
    describe:   'అత్యవసర పరిస్థితిని వివరించండి',
    placeholder:'🎙 నొక్కి ఏమి జరుగుతుందో చెప్పండి...',
    typehere:   'ఉదా. మా అంకుల్ పడిపోయారు, శ్వాస తీసుకోవడం లేదు...',
    or:         'లేదా క్రింద టైప్ చేయండి',
    analyze:    '⚡ అత్యవసర ప్రణాళిక పొందండి',
    analyzing:  'అత్యవసర పరిస్థితి విశ్లేషిస్తున్నారు...',
    idleTitle:  'స్పందించడానికి సిద్ధంగా ఉంది',
    idleSub:    'మాట్లాడండి లేదా టైప్ చేయండి. FirstVoice మీకు ఏమి చేయాలో చెప్తుంది.',
    steps:      'చర్య దశలు',
    donot:      'చేయకూడదు',
    dispatch:   '📡 అత్యవసర సారాంశం',
    tts:        '🔊 బిగ్గరగా చదవండి',
    listening:  'వింటున్నాను...',
    speechErr:  'వాయిస్ అందుబాటులో లేదు. దయచేసి టైప్ చేయండి.',
    noInput:    'అత్యవసర పరిస్థితిని తెలియజేయండి.',
  },
  mr: {
    describe:   'आणीबाणीचे वर्णन करा',
    placeholder:'🎙 दाबा आणि काय होत आहे ते सांगा...',
    typehere:   'उदा. माझे काका पडले, श्वास घेत नाहीत...',
    or:         'किंवा खाली टाइप करा',
    analyze:    '⚡ आणीबाणी योजना मिळवा',
    analyzing:  'आणीबाणी विश्लेषण होत आहे...',
    idleTitle:  'प्रतिसाद देण्यास तयार',
    idleSub:    'बोला किंवा टाइप करा. FirstVoice तुम्हाला काय करायचे ते सांगेल.',
    steps:      'कृती पायऱ्या',
    donot:      'हे करू नका',
    dispatch:   '📡 आणीबाणी सारांश',
    tts:        '🔊 मोठ्याने वाचा',
    listening:  'ऐकत आहे...',
    speechErr:  'व्हॉइस उपलब्ध नाही. कृपया टाइप करा.',
    noInput:    'कृपया आणीबाणी सांगा.',
  }
};

const langSpeechCodes = {
  en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN',
  ta: 'ta-IN', te: 'te-IN', mr: 'mr-IN'
};

// ─── LANGUAGE ────────────────────────────────────────────
function setLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.lang-chip').forEach(c => {
    c.classList.toggle('active', c.dataset.lang === lang);
  });
  const t = i18n[lang];
  document.getElementById('lbl-describe').textContent     = t.describe;
  document.getElementById('lbl-or').textContent           = t.or;
  document.getElementById('lbl-analyzing').textContent    = t.analyzing;
  document.getElementById('lbl-idle-title').textContent   = t.idleTitle;
  document.getElementById('lbl-idle-sub').textContent     = t.idleSub;
  document.getElementById('analyzeBtn').textContent       = t.analyze;
  document.getElementById('manualInput').placeholder      = t.typehere;
  const tp = document.getElementById('transcriptPlaceholder');
  if (tp) tp.textContent = t.placeholder;
  if (!currentTranscript) setTranscriptPlaceholder();
}

function t(key) { return (i18n[currentLang] || i18n.en)[key] || key; }

// ─── TRANSCRIPT ───────────────────────────────────────────
function setTranscriptPlaceholder() {
  const box = document.getElementById('transcriptBox');
  box.innerHTML = `<span class="transcript-placeholder">${t('placeholder')}</span>`;
}

function updateTranscript(text, listening) {
  const box = document.getElementById('transcriptBox');
  currentTranscript = text;
  if (text) {
    box.textContent = text;
  } else {
    box.innerHTML = `<span class="transcript-placeholder">${listening ? t('listening') : t('placeholder')}</span>`;
  }
  box.className = 'transcript-box' + (listening ? ' listening' : '');
  if (listening && !text) {
    const wf = document.createElement('div');
    wf.className = 'waveform';
    for (let i = 0; i < 9; i++) {
      const b = document.createElement('div');
      b.className = 'wave-bar';
      b.style.animationDelay = `${i * 0.1}s`;
      wf.appendChild(b);
    }
    box.appendChild(wf);
  }
}

// ─── MIC ─────────────────────────────────────────────────
function toggleMic() {
  if (isListening) stopMic();
  else startMic();
}

function startMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { showError(t('speechErr')); return; }

  recognition = new SR();
  recognition.continuous    = true;
  recognition.interimResults = true;
  recognition.lang = langSpeechCodes[currentLang] || 'en-IN';

  recognition.onstart = () => {
    isListening = true;
    document.getElementById('micBtn').textContent = '⏹';
    document.getElementById('micBtn').classList.add('recording');
    updateTranscript('', true);
  };

  recognition.onend = () => {
    isListening = false;
    document.getElementById('micBtn').textContent = '🎙';
    document.getElementById('micBtn').classList.remove('recording');
    if (!currentTranscript) updateTranscript('', false);
  };

  recognition.onresult = (e) => {
    let final = '';
    for (let i = 0; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript + ' ';
    }
    if (final.trim()) updateTranscript(final.trim(), true);
  };

  recognition.onerror = (e) => {
    isListening = false;
    showError('Mic error: ' + e.error);
  };

  recognition.start();
}

function stopMic() {
  recognition && recognition.stop();
  isListening = false;
}

// ─── ANALYZE ─────────────────────────────────────────────
async function analyze() {
  const manual  = document.getElementById('manualInput').value.trim();
  const input   = currentTranscript || manual;

  if (!input)  { showError(t('noInput')); return; }

  const analyzeBtn = document.getElementById('analyzeBtn');
  const micBtn = document.getElementById('micBtn');

  stopMic();
  analyzeBtn.disabled = true;
  micBtn.disabled = true;
  hideError();
  showLoading(true);
  showResponse(null);
  showIdle(false);

  try {
    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    showLoading(false);
    renderResponse(data);
    speakFirstStep(data);
  } catch (err) {
    showLoading(false);
    showIdle(false);
    showError(err.message);
  } finally {
    analyzeBtn.disabled = false;
    micBtn.disabled = false;
  }
}

// ─── RENDER RESPONSE ─────────────────────────────────────
function getSeverityClass(s) {
  if (!s) return 'badge-moderate';
  s = s.toUpperCase();
  if (s === 'CRITICAL') return 'badge-critical';
  if (s === 'SERIOUS')  return 'badge-serious';
  return 'badge-moderate';
}

function getSevColorClass(s) {
  if (!s) return 'sev-moderate';
  s = s.toUpperCase();
  if (s === 'CRITICAL') return 'sev-critical';
  if (s === 'SERIOUS')  return 'sev-serious';
  return 'sev-moderate';
}

function getEmoji(type) {
  if (!type) return '🚨';
  const t = type.toLowerCase();
  if (t.includes('cardiac') || t.includes('heart') || t.includes('हृदय') || t.includes('ಹೃದಯ')) return '💔';
  if (t.includes('seizure') || t.includes('epilep') || t.includes('दौरा') || t.includes('ಸೆಳವು')) return '⚡';
  if (t.includes('stroke') || t.includes('brain') || t.includes('ಪಾರ್ಶ್ವ')) return '🧠';
  if (t.includes('chok') || t.includes('drown')) return '😶';
  if (t.includes('breath')) return '🫁';
  if (t.includes('fall') || t.includes('fracture') || t.includes('bone')) return '🦴';
  return '🚨';
}

function renderResponse(d) {
  const box = document.getElementById('responseBox');
  const sevClass   = getSeverityClass(d.severity);
  const sevColor   = getSevColorClass(d.severity);
  const emoji      = getEmoji(d.emergencyType);

  let stepsHtml = (d.steps || []).map(s => `
    <div class="step-row">
      <div class="step-num">${s.step}</div>
      <div>
        <div class="step-action">${s.action}</div>
        <div class="step-detail">${s.detail}</div>
      </div>
    </div>
  `).join('');

  let donotHtml = (d.doNot || []).map(item => `
    <div class="donot-item"><span class="donot-x">✕</span>${item}</div>
  `).join('');

  const ttsText = (d.steps || []).map((s,i) => `Step ${i+1}: ${s.action}. ${s.detail}`).join('. ');

  box.innerHTML = `
    <!-- Badge -->
    <div class="emergency-badge ${sevClass}" style="margin-bottom:12px;">
      <div class="badge-emoji">${emoji}</div>
      <div>
        <div class="badge-type">${d.emergencyType || ''}</div>
        <div class="badge-sev ${sevColor}">${d.severity || ''} — ACT NOW</div>
        ${d.detectedLanguage ? `<div class="badge-lang">DETECTED: ${d.detectedLanguage.toUpperCase()}</div>` : ''}
      </div>
    </div>

    <!-- Steps -->
    <div class="card" style="margin-bottom:12px;">
      <h2 class="card-label">${t('steps')}</h2>
      <div class="steps-list">${stepsHtml}</div>
      <button class="tts-btn" onclick="speakText(window.currentTTS)">${t('tts')}</button>
    </div>

    <!-- Do Not -->
    ${donotHtml ? `
    <div class="donot-card" style="margin-bottom:12px;">
      <div class="donot-heading">${t('donot')}</div>
      ${donotHtml}
    </div>` : ''}

    <!-- Dispatch -->
    ${d.dispatchSummary ? `
    <div class="dispatch-card" style="margin-bottom:12px;">
      <div class="dispatch-heading">${t('dispatch')}</div>
      <div class="dispatch-text">${d.dispatchSummary}</div>
    </div>` : ''}

    <!-- Reassurance -->
    ${d.reassurance ? `
    <div class="reassurance-card" style="margin-bottom:12px;">
      💬 ${d.reassurance}
    </div>` : ''}
  `;

  // Fix XSS vulnerability by not injecting string into onclick
  window.currentTTS = ttsText;

  box.style.display = 'block';
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─── TTS ─────────────────────────────────────────────────
function speakText(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = langSpeechCodes[currentLang] || 'en-IN';
  u.rate = 0.88; u.pitch = 0.85;
  window.speechSynthesis.speak(u);
}

function speakFirstStep(d) {
  if (!d.steps || !d.steps[0]) return;
  const msg = `${d.emergencyType}. Step 1: ${d.steps[0].action}. ${d.steps[0].detail}`;
  speakText(msg);
}

// ─── UI HELPERS ──────────────────────────────────────────
function showLoading(v) { document.getElementById('loadingBox').style.display = v ? 'flex' : 'none'; }
function showIdle(v)    { document.getElementById('idleBox').style.display    = v ? 'flex' : 'none'; }
function showResponse(v){ if (!v) document.getElementById('responseBox').style.display = 'none'; }
function showError(msg) { const e = document.getElementById('errorBox'); e.textContent = '⚠ ' + msg; e.style.display = 'block'; }
function hideError()    { document.getElementById('errorBox').style.display = 'none'; }

function resetAll() {
  currentTranscript = '';
  document.getElementById('manualInput').value = '';
  stopMic();
  updateTranscript('', false);
  showResponse(null);
  hideError();
  showLoading(false);
  showIdle(true);
  window.speechSynthesis && window.speechSynthesis.cancel();
}

// ─── INIT ────────────────────────────────────────────────
setLang('en');