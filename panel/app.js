'use strict';
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const actions = ['BUILD', 'CHICKEN', 'PHOENIX', 'SKY_WHALE', 'WIN', 'ZAP', 'TNT', 'BLACK_HOLE', 'TORNADO', 'LOSE'];
const names = {
  BUILD: 'CONSTRUÇÃO',
  CHICKEN: 'GALINHA',
  PHOENIX: 'FÊNIX',
  SKY_WHALE: 'SKY WHALE',
  WIN: '+1 VITÓRIA',
  ZAP: 'RAIO',
  TNT: 'EXPLOSÃO TNT',
  BLACK_HOLE: 'BURACO NEGRO',
  TORNADO: 'TORNADO',
  LOSE: '−1 VITÓRIA'
};

const defaultBadges = {
  BUILD: '🧱',
  CHICKEN: '🐔',
  PHOENIX: '🦅',
  SKY_WHALE: '🐋',
  WIN: '🏆',
  ZAP: '⚡',
  TNT: '💣',
  BLACK_HOLE: '🕳️',
  TORNADO: '🌪️',
  LOSE: '💀'
};

function description(a) {
  const n = cfg?.amounts?.[a] ?? 1;
  if (a === 'WIN') return `Ganha ${n} vitória(s)`;
  if (a === 'LOSE') return `Perde ${n} vitória(s)`;
  return `${actions.indexOf(a) < 5 ? 'Constrói' : 'Destrói'} ${n} blocos`;
}

let cfg, token, saveTimer, toastTimer, lastState, saving = false, dirty = false;

function toast(message, error = false) {
  const e = $('#toast');
  if (!e) return;
  e.textContent = message;
  e.className = error ? 'error' : '';
  e.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { e.style.display = 'none'; }, 4000);
}

async function api(path, body) {
  const r = await fetch('/api/' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-B7-Token': token || ''
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  let data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw Error(typeof data.detail === 'string' ? data.detail : (data.message || 'Erro de comunicação com o jogo.'));
  }
  return data;
}

function get(path) {
  return path.split('.').reduce((o, k) => (o ? o[k] : undefined), cfg);
}

function set(path, val) {
  let a = path.split('.'), o = cfg;
  for (const k of a.slice(0, -1)) {
    if (!o[k]) o[k] = {};
    o = o[k];
  }
  o[a.at(-1)] = val;
}

function syncSkinCards() {
  const cur = cfg?.skin_preset || 'rei_coroa';
  $$('.skin-card').forEach(c => {
    const active = c.dataset.skin === cur;
    c.classList.toggle('selected', active);
    const b = c.querySelector('.btn-equip');
    if (b) {
      b.textContent = active ? '✓ EQUIPADA' : 'Equipar Skin';
      b.className = active ? 'primary btn-equip is-equipped' : 'btn-equip';
    }
  });
  $$('[data-field="skin_preset"]').forEach(s => { s.value = cur; });
}

function equipSkin(skin) {
  if (!cfg || !skin) return;
  cfg.skin_preset = skin;
  syncSkinCards();
  dirty = true;
  save(true);
  const title = $$(`.skin-card[data-skin="${skin}"] h4`)[0]?.textContent || skin;
  toast('Skin equipada e salva com sucesso: ' + title);
}

function bindFields(root = document) {
  syncSkinCards();
  root.querySelectorAll('[data-field]').forEach(e => {
    const p = e.dataset.field;
    if (e.type === 'checkbox') e.checked = !!get(p);
    else e.value = get(p) ?? '';

    const handleChange = () => {
      if (!e.checkValidity()) {
        e.reportValidity();
        return;
      }
      const val = e.type === 'checkbox' ? e.checked : ['number', 'range'].includes(e.type) ? Number(e.value) : e.value;
      set(p, val);
      $$(`[data-field="${p}"]`).filter(x => x !== e).forEach(x => {
        if (x.type === 'checkbox') x.checked = e.checked;
        else x.value = e.value;
      });
      if (p === 'skin_preset') {
        syncSkinCards();
      }
      scheduleSave();
    };

    e.onchange = handleChange;
    if (e.type === 'number' || e.type === 'range') {
      e.oninput = handleChange;
    }
  });
}

function scheduleSave() {
  $$('[data-description]').forEach(e => {
    e.textContent = description(e.dataset.description);
  });
  dirty = true;
  const s = $('#saved');
  if (s) s.textContent = 'Salvando…';
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => save(false), 800);
}

async function save(force = false) {
  if (saving) return;
  if (!force && !dirty) return;
  saving = true;
  dirty = false;

  const saveLabel = $('#saved');
  const allSaveButtons = $$('.btnSaveTrigger, #btnSaveConfig');
  if (saveLabel) saveLabel.textContent = 'Salvando…';
  allSaveButtons.forEach(b => {
    b.disabled = true;
    b.textContent = '⏳ Salvando...';
  });

  try {
    const payload = JSON.parse(JSON.stringify(cfg));
    // Clean up mappings so empty new rows don't crash backend validation
    payload.mappings = (payload.mappings || []).filter(m => (m.gift_id && m.gift_id.trim()) || (m.gift_name && m.gift_name.trim()));
    await api('settings', payload);

    if (saveLabel) saveLabel.textContent = '✓ Configurações salvas';
    allSaveButtons.forEach(b => {
      b.textContent = '✓ Salvo com Sucesso!';
      b.style.borderColor = '#22c55e';
    });
    setTimeout(() => {
      allSaveButtons.forEach(b => {
        b.disabled = false;
        b.textContent = '💾 Salvar Configurações';
        b.style.borderColor = '';
      });
    }, 1800);
    toast('✓ Configurações salvas com sucesso!');
  } catch (err) {
    if (saveLabel) saveLabel.textContent = 'Alteração não salva';
    allSaveButtons.forEach(b => {
      b.disabled = false;
      b.textContent = '⚠️ Erro ao Salvar';
    });
    toast(err.message, true);
  } finally {
    saving = false;
    if (dirty) scheduleSave();
  }
}

function options(selected) {
  return actions.map(a => `<option value="${a}" ${a === selected ? 'selected' : ''}>${names[a] || a} — ${description(a)}</option>`).join('');
}

function mappingRows() {
  const box = $('#mappingRows');
  if (!box) return;
  box.replaceChildren();
  const emptyHint = $('#mappingEmpty');
  if (emptyHint) emptyHint.hidden = cfg.mappings.length > 0;

  cfg.mappings.forEach((m, i) => {
    const row = document.createElement('div');
    row.className = 'mapping-row';
    row.innerHTML = `
      <div class="mapping-fields">
        <label>
          <span>ID do Presente (TikTok)</span>
          <input class="map-id" placeholder="Ex: 5655" aria-label="ID do presente" value="${m.gift_id || ''}">
        </label>
        <label>
          <span>Nome Exato do Presente</span>
          <input class="map-name" placeholder="Ex: Rosa, Mini Carro..." aria-label="Nome do presente" value="${m.gift_name || ''}">
        </label>
        <label>
          <span>Ação Acionada</span>
          <select class="map-action" aria-label="Ação acionada">
            ${options(m.action)}
          </select>
        </label>
      </div>
      <button class="btn-remove-map" type="button" title="Remover este presente">✕ Excluir</button>
    `;

    const idInput = row.querySelector('.map-id');
    const nameInput = row.querySelector('.map-name');
    const actionSelect = row.querySelector('.map-action');

    const updateRow = () => {
      m.gift_id = idInput.value.trim();
      m.gift_name = nameInput.value.trim();
      m.action = actionSelect.value;
      scheduleSave();
    };

    idInput.addEventListener('input', updateRow);
    idInput.addEventListener('change', updateRow);
    nameInput.addEventListener('input', updateRow);
    nameInput.addEventListener('change', updateRow);
    actionSelect.addEventListener('change', updateRow);

    row.querySelector('.btn-remove-map').onclick = () => {
      cfg.mappings.splice(i, 1);
      mappingRows();
      scheduleSave();
      toast('Vínculo de presente removido.');
    };

    box.append(row);
  });
}

function buildForms() {
  if (!cfg.action_badges) {
    cfg.action_badges = Object.assign({}, defaultBadges);
  }

  // Clear previous items
  const amountsBox = $('#amounts');
  const testBox = $('#testActions');
  if (amountsBox) amountsBox.replaceChildren();
  if (testBox) testBox.replaceChildren();

  for (const a of actions) {
    const card = document.createElement('div');
    card.className = 'action-item';
    card.innerHTML = `
      <div class="action-item-head">
        <img src="/assets/icon_${a}.png" alt="${a}" class="action-item-icon">
        <div class="action-item-info">
          <strong class="action-item-name">${names[a] || a}</strong>
          <span class="action-item-desc" data-description="${a}">${description(a)}</span>
        </div>
      </div>
      <div class="action-item-fields">
        <label>
          <span>Multiplicador (Blocos/Vitória)</span>
          <input type="number" min="1" max="10000" data-field="amounts.${a}">
        </label>
        <label>
          <span>Foto / Emoji no Topo (HUD)</span>
          <input type="text" placeholder="Ex: 🧱 ou URL da foto" class="badge-input" data-badge-action="${a}" maxlength="2000" value="${cfg.action_badges[a] || defaultBadges[a] || ''}">
        </label>
      </div>
    `;

    const badgeInput = card.querySelector('.badge-input');
    const updateBadge = () => {
      cfg.action_badges[a] = badgeInput.value.trim();
      scheduleSave();
    };
    badgeInput.addEventListener('input', updateBadge);
    badgeInput.addEventListener('change', updateBadge);

    if (amountsBox) amountsBox.append(card);

    // Test action buttons
    if (testBox) {
      const b = document.createElement('button');
      b.innerHTML = `<img src="/assets/icon_${a}.png" alt=""><span>${names[a] || a}</span><small class="effect-description" data-description="${a}">${description(a)}</small>`;
      b.onclick = () => simulate(a);
      testBox.append(b);
    }
  }

  const rulesBox = $('#rules');
  if (rulesBox) {
    rulesBox.replaceChildren();
    for (const [key, title] of Object.entries({ likes: 'Curtidas', follows: 'Novo seguidor', comments: 'Comentário', shares: 'Compartilhamento' })) {
      const row = document.createElement('div');
      row.className = 'rule';
      row.innerHTML = `
        <label class="rule-title"><input type="checkbox" data-field="${key}.enabled">${title}</label>
        <div class="form-grid">
          <label>Ação<select data-field="${key}.action">${options(cfg[key].action)}</select></label>
          <label>Blocos/vitórias por ação<input type="number" min="1" max="1000" data-field="${key}.amount"></label>
          <label>Intervalo por pessoa (s)<input type="number" min="0" max="3600" data-field="${key}.cooldown"></label>
          ${key === 'likes' ? `<label>A cada X curtidas<input type="number" min="1" max="100000" data-field="${key}.threshold"></label>` : ''}
          ${key === 'comments' ? `<label>Palavra exata<input maxlength="80" data-field="${key}.word"></label>` : ''}
        </div>
      `;
      rulesBox.append(row);
    }
  }

  bindFields();
  mappingRows();

  // Attach skin card handlers
  $$('.skin-card').forEach(c => {
    c.onclick = (e) => {
      const skin = c.dataset.skin;
      if (skin) equipSkin(skin);
    };
  });
}

async function simulate(action = 'BUILD', kind = 'gift') {
  try {
    const count = Number($('#testCount').value) || 1;
    const r = await api('simulate', {
      action,
      kind,
      name: $('#testName').value || 'Bruno',
      avatar: $('#testAvatar').value || '',
      count,
      combo: $('#testCombo').checked && kind === 'gift',
      comment: $('#testComment').value || 'construir'
    });
    const sum = (r.applied || []).reduce((v, x) => v + x.applied, 0);
    const pending = (r.applied || []).reduce((v, x) => v + x.pending, 0);
    toast((r.applied && r.applied.length) ? `Aplicado no jogo: ${sum > 0 ? '+' : ''}${sum}${pending ? ' · ' + pending + ' na fila' : ''}` : 'Sem efeito: inicie a partida ou confira os limites.');
  } catch (e) {
    toast(e.message, true);
  }
}

function update(s) {
  lastState = s;
  $('#progress').textContent = s.progress + '%';
  $('#progressBar').style.width = s.progress + '%';
  $('#wins').textContent = `${s.wins} / ${s.goal}`;
  $('#round').textContent = 'Rodada ' + s.round;
  $('#blocks').textContent = `${s.blocks} / ${s.capacity} blocos`;

  $('#phase').textContent = !s.running ? 'Pausado' : ({ building: 'Construindo', defending: 'Defesa ' + Math.ceil(s.timer) + 's', celebrating: 'Vitória!', goal: 'Meta!' }[s.phase] || s.phase);
  $('#modeBadge').textContent = s.config.mode === 'test' ? 'MODO TESTE' : 'MODO LIVE';
  $('#modeBadge').className = 'badge ' + (s.config.mode === 'live' ? 'live' : '');

  const c = s.connection;
  $('#connectionBadge').textContent = ({ offline: 'OFFLINE', connecting: 'CONECTANDO', connected: 'AO VIVO', reconnecting: 'RECONECTANDO', error: 'ERRO' }[c.status] || c.status);
  $('#connectionBadge').className = 'badge ' + (c.status === 'connected' ? 'live' : '');
  $('#connectionMessage').textContent = c.message;

  const keySavedEl = $('#keySavedStatus');
  if (keySavedEl) {
    keySavedEl.style.display = s.key_saved ? 'inline' : 'none';
  }
  $('#keyHint').textContent = s.key_saved ? `Chave Euler salva na máquina (${s.key_preview || '••••••••'}). Deixe o campo vazio para reutilizar.` : 'A chave fica protegida neste computador.';

  $('#diagnostic').textContent = `${s.fps} FPS · Fila: ${s.queue} · Eventos recebidos: ${c.received}`;
  $('#notice').textContent = s.notice;
  $('#logs').textContent = s.logs.join('\n');

  const cat = $('#catalog');
  if (cat && s.catalog && s.catalog.length) {
    cat.replaceChildren();
    s.catalog.forEach(g => {
      const row = document.createElement('div');
      row.style.margin = '4px 0';
      row.textContent = `${g.name} · ID ${g.id} `;
      const b = document.createElement('button');
      b.textContent = 'Vincular';
      b.onclick = () => {
        cfg.mappings.push({ gift_id: String(g.id), gift_name: g.name, action: 'BUILD' });
        mappingRows();
        scheduleSave();
        toast(`Presente ${g.name} vinculado!`);
      };
      row.append(b);
      cat.append(row);
    });
  }
}

function websocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);
  ws.onopen = () => ws.send(JSON.stringify({ token }));
  ws.onmessage = e => {
    try {
      update(JSON.parse(e.data));
    } catch (_) {}
  };
  ws.onclose = () => {
    setTimeout(websocket, 1500);
  };
  ws.onerror = () => {
    const cm = $('#connectionMessage');
    if (cm) cm.textContent = 'Reconectando ao jogo…';
  };
}

async function init() {
  try {
    const sessionData = await api('session');
    token = sessionData.token;
    const state = await api('state');
    cfg = state.config;
    $('#username').value = cfg.username || '';
    buildForms();
    update(state);
    websocket();
  } catch (e) {
    toast('Não foi possível conectar ao jogo: ' + e.message, true);
  }
}

// Navigation Tabs
$$('nav button').forEach(b => {
  b.onclick = () => {
    $$('nav button').forEach(x => x.classList.toggle('active', x === b));
    $$('.page').forEach(x => x.classList.toggle('active', x.id === b.dataset.tab));
    $('#pageTitle').textContent = {
      home: 'Visão geral',
      skins: 'Skins do Personagem',
      game: 'Configurar jogo',
      interactions: 'Interações & Presentes',
      tests: 'Modo de teste'
    }[b.dataset.tab] || 'Painel';
  };
});

// Top and section Save buttons
$$('.btnSaveTrigger, #btnSaveConfig').forEach(b => {
  b.onclick = () => {
    save(true);
  };
});

// Game Commands (Start, Pause, Restart)
$$('[data-command]').forEach(b => {
  b.onclick = async () => {
    try {
      await api('game/' + b.dataset.command, {});
      toast('Comando aplicado.');
    } catch (e) {
      toast(e.message, true);
    }
  };
});

// TikTok Connect
$('#connect').onclick = async () => {
  const b = $('#connect');
  b.disabled = true;
  try {
    const username = $('#username').value.trim();
    const key = $('#key').value.trim();
    await api('connect', { username, key });
    $('#key').value = '';
    cfg.username = username;
    cfg.mode = 'live';
    bindFields();
    toast('Conexão iniciada com a Live de @' + username);
  } catch (e) {
    toast(e.message, true);
  } finally {
    b.disabled = false;
  }
};

// Save Euler Key Button
const btnSaveKey = $('#btnSaveKey');
if (btnSaveKey) {
  btnSaveKey.onclick = async () => {
    const key = $('#key').value.trim();
    if (!key) {
      toast('Digite a chave Euler no campo ao lado antes de salvar.', true);
      return;
    }
    btnSaveKey.disabled = true;
    try {
      await api('save-key', { key });
      $('#key').value = '';
      const keySavedEl = $('#keySavedStatus');
      if (keySavedEl) keySavedEl.style.display = 'inline';
      toast('✓ Chave Euler salva com sucesso no computador!');
    } catch (e) {
      toast(e.message, true);
    } finally {
      btnSaveKey.disabled = false;
    }
  };
}

// Disconnect
$('#disconnect').onclick = async () => {
  try {
    await api('disconnect', {});
    toast('Live desconectada.');
  } catch (e) {
    toast(e.message, true);
  }
};

// Add Mapping
$('#addMapping').onclick = () => {
  if (!cfg.mappings) cfg.mappings = [];
  cfg.mappings.push({ gift_id: '', gift_name: '', action: 'BUILD' });
  mappingRows();
  scheduleSave();
};

// Simulated events
$$('[data-event]').forEach(b => {
  b.onclick = () => simulate('BUILD', b.dataset.event);
});

// Initialize app
init();
