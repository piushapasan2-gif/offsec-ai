// ═══════════════════════════════════════
//  OffSec AI 2025 - Frontend (auth-gated)
// ═══════════════════════════════════════

// ─── Auth bootstrap ───
const JWT = localStorage.getItem('offsec_jwt');
if (!JWT) { location.href = '/login'; }

// fetch wrapper that injects Authorization header + handles 401 → login
async function api(path, opts = {}) {
  const headers = Object.assign(
    {'Authorization': 'Bearer ' + JWT, 'Content-Type': 'application/json'},
    opts.headers || {}
  );
  const r = await fetch(path, Object.assign({}, opts, {headers}));
  if (r.status === 401) {
    localStorage.removeItem('offsec_jwt');
    location.href = '/login';
    return;
  }
  return r;
}

// ─── Matrix rain ───
(function () {
  const cvs = document.getElementById('matrix');
  const ctx = cvs.getContext('2d');
  function R() { cvs.width = innerWidth; cvs.height = innerHeight; }
  R(); addEventListener('resize', R);
  const ch = 'アイウエオ01ABCDEF<>{}[]/\\#@!*+=';
  const cols = Math.floor(cvs.width / 14);
  const drops = Array(cols).fill(1);
  setInterval(() => {
    ctx.fillStyle = 'rgba(5,10,12,0.06)';
    ctx.fillRect(0, 0, cvs.width, cvs.height);
    ctx.fillStyle = '#00ff9c';
    ctx.font = '13px monospace';
    for (let i = 0; i < drops.length; i++) {
      ctx.fillText(ch[Math.floor(Math.random()*ch.length)], i*14, drops[i]*14);
      if (drops[i]*14 > cvs.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }, 60);
})();

// ─── Socket.IO with JWT ───
const socket = io({ auth: { token: JWT }, query: { token: JWT } });
const dot = document.getElementById('dot');
const statusText = document.getElementById('status-text');
socket.on('connect', () => {
  dot.classList.remove('off'); dot.classList.add('on');
  statusText.textContent = 'connected';
});
socket.on('disconnect', () => {
  dot.classList.remove('on'); dot.classList.add('off');
  statusText.textContent = 'disconnected';
});
socket.on('log', (d) => {
  const el = document.getElementById('console-output');
  if (el) el.textContent = `[${new Date().toLocaleTimeString()}] [${d.level}] ${d.msg}\n` + el.textContent;
});

// ─── State ───
let SESSION_ID = localStorage.getItem('offsec_session') || null;
let CURRENT_USER = null;

// ─── Boot ───
async function boot() {
  // Identity
  const meR = await api('/api/auth/me');
  if (!meR) return;
  const me = await meR.json();
  CURRENT_USER = me.user;

  // LLMs
  const llm = await (await api('/api/llm/status')).json();
  const llmList = document.getElementById('llm-list');
  const prefer = document.getElementById('prefer');
  llmList.innerHTML = '';
  for (const [name, ok] of Object.entries(llm.all_keys)) {
    const row = document.createElement('div');
    row.className = 'provider-row';
    row.innerHTML = `<span>${name}</span><span class="${ok ? 'ok' : 'ko'}">${ok ? '✔' : '✘'}</span>`;
    llmList.appendChild(row);
    if (ok) {
      const opt = document.createElement('option');
      opt.value = name; opt.textContent = name;
      prefer.appendChild(opt);
    }
  }
  document.getElementById('provider-info').textContent =
    `${CURRENT_USER.email || 'user'} · ${llm.configured.length} LLMs`;

  // Intel
  const intel = await (await api('/api/intel/status')).json();
  const intelList = document.getElementById('intel-list');
  const intelProv = document.getElementById('intel-provider');
  intelList.innerHTML = '';
  for (const [name, ok] of Object.entries(intel)) {
    const row = document.createElement('div');
    row.className = 'provider-row';
    row.innerHTML = `<span>${name}</span><span class="${ok ? 'ok' : 'ko'}">${ok ? '✔' : '✘'}</span>`;
    intelList.appendChild(row);
    if (ok) {
      const opt = document.createElement('option');
      opt.value = name; opt.textContent = name;
      intelProv.appendChild(opt);
    }
  }
  updateIntelActions();
  intelProv.addEventListener('change', updateIntelActions);

  // Scope
  const scope = await (await api('/api/scope')).json();
  document.getElementById('scope-info').innerHTML =
    `mode: <b>${scope.mode}</b><br>engagement: ${scope.current || '<i>none</i>'}`;

  // Quotas
  const q = await (await api('/api/quotas')).json();
  document.getElementById('quotas').innerHTML = Object.entries(q)
    .map(([k,v]) => `${k}: ${v.used}/${v.limit}`).join('<br>') || '<i>no usage yet</i>';
}

const INTEL_ACTIONS = {
  shodan: ['host','search','info','myip'],
  virustotal: ['ip','domain','hash','url_scan'],
  otx: ['ip','domain','hash','pulses'],
  abuseipdb: ['check'],
  urlscan: ['submit','result','search'],
  ipinfo: ['lookup','myip'],
  cve: ['lookup','search','critical'],
  github: ['code','repo','commits','org'],
  fullhunt: ['domain','subdomains'],
  leakix: ['host','search'],
};
function updateIntelActions() {
  const p = document.getElementById('intel-provider').value;
  const sel = document.getElementById('intel-action');
  sel.innerHTML = '';
  (INTEL_ACTIONS[p] || []).forEach(a => {
    const o = document.createElement('option');
    o.value = a; o.textContent = a;
    sel.appendChild(o);
  });
}

// ─── Chat ───
function appendMsg(role, content, meta) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;
  const html = content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, (m, c) => `<pre>${c}</pre>`)
    .replace(/`([^`]+)`/g, (m, c) => `<code>${c}</code>`)
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  wrap.innerHTML = html;
  if (meta) {
    const m = document.createElement('div'); m.className = 'meta';
    m.textContent = meta;
    wrap.appendChild(m);
  }
  const list = document.getElementById('messages');
  list.appendChild(wrap);
  list.scrollTop = list.scrollHeight;
}

document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;
  const prefer = document.getElementById('prefer').value || null;
  const target = document.getElementById('target').value.trim() || null;
  appendMsg('user', prompt);
  document.getElementById('prompt').value = '';
  const thinking = document.getElementById('thinking');
  thinking.classList.remove('hidden');
  document.getElementById('thinking-text').textContent =
    `routing… ${prefer ? '[' + prefer + ']' : '[auto]'}`;
  try {
    const r = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({prompt, session_id: SESSION_ID, prefer, target}),
    });
    if (!r) return;
    const data = await r.json();
    thinking.classList.add('hidden');
    if (!data.ok) {
      appendMsg('assistant', `[!] ${data.error || 'error'}`);
      return;
    }
    SESSION_ID = data.session_id;
    localStorage.setItem('offsec_session', SESSION_ID);
    appendMsg('assistant', data.content,
      `via ${data.provider} (${data.model}) · ${data.task_type} · ${data.elapsed_ms}ms`);
  } catch (err) {
    thinking.classList.add('hidden');
    appendMsg('assistant', '[!] network error: ' + err);
  }
});

document.getElementById('prompt').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    document.getElementById('chat-form').requestSubmit();
  }
});

// ─── Tabs ───
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-' + t.dataset.tab).classList.add('active');
    if (t.dataset.tab === 'audit') refreshAudit();
  });
});

// ─── Intel ───
document.getElementById('intel-run').addEventListener('click', async () => {
  const provider = document.getElementById('intel-provider').value;
  const action = document.getElementById('intel-action').value;
  const arg = document.getElementById('intel-arg').value.trim();
  if (!provider || !arg) return;
  const out = document.getElementById('intel-output');
  out.textContent = 'querying…';
  const argMap = {
    host:'ip', ip:'ip', domain:'domain', hash:'hash_', search:'query',
    code:'query', repo:'query', commits:'query', org:'org', lookup:'cve_id',
    check:'ip', submit:'url', result:'uuid', pulses:'query',
    critical:'days', subdomains:'domain',
  };
  const argName = argMap[action] || 'query';
  let args;
  if (action === 'lookup' && provider === 'ipinfo') args = {ip: arg};
  else if (action === 'critical') args = {days: parseInt(arg) || 7};
  else args = {[argName]: arg};
  try {
    const r = await api(`/api/intel/${provider}`, {
      method: 'POST', body: JSON.stringify({action, args}),
    });
    out.textContent = JSON.stringify(await r.json(), null, 2);
  } catch (err) { out.textContent = 'error: ' + err; }
});

// ─── Audit ───
async function refreshAudit() {
  const r = await api('/api/audit');
  const data = await r.json();
  document.getElementById('audit-output').textContent =
    data.map(e => {
      const ts = typeof e.ts === 'number'
        ? new Date(e.ts*1000).toLocaleTimeString()
        : new Date(e.ts).toLocaleTimeString();
      const p = typeof e.payload === 'string' ? e.payload : JSON.stringify(e.payload);
      return `[${ts}] ${e.event}  ${p.slice(0,80)}`;
    }).join('\n');
}
document.getElementById('audit-refresh').addEventListener('click', refreshAudit);

// ─── Logout ───
function logout() {
  localStorage.removeItem('offsec_jwt');
  localStorage.removeItem('offsec_refresh');
  localStorage.removeItem('offsec_session');
  location.href = '/login';
}
window.offsecLogout = logout;

boot();
