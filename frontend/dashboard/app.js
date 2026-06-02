const state = {
  graph: null,
  tasks: [],
  runs: [],
  feed: [],
  expandedTaskId: null,
  createRunTaskId: null,
  selectedRunId: null,
  selectedRun: null,
  ws: null,
  wsRetries: 0,
  wsReconnectTimer: null,
  autoScroll: true,
  runAutoRefresh: null,
  transitionEvent: null,
};

const MAX_FEED_EVENTS = 600;
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const MAX_RETRY_EXPONENT = 6;
const TRANSITION_ANIMATION_DURATION_MS = 1500;

const STATUS_CLASS = {
  CREATED: 'status-CREATED',
  RUNNING: 'status-RUNNING',
  PAUSED: 'status-PAUSED',
  WAITING_APPROVAL: 'status-WAITING_APPROVAL',
  COMPLETED: 'status-COMPLETED',
  FAILED: 'status-FAILED',
  CANCELLED: 'status-CANCELLED',
  QUEUED: 'status-QUEUED',
};

const ACTIVE_COMMANDS = {
  CREATED: ['START', 'CANCEL'],
  RUNNING: ['PAUSE', 'CANCEL'],
  PAUSED: ['RESUME', 'CANCEL'],
  WAITING_APPROVAL: ['APPROVE', 'CANCEL'],
  COMPLETED: [],
  FAILED: [],
  CANCELLED: [],
};

const graphLayout = {
  client: { x: 80, y: 70 },
  po: { x: 220, y: 70 },
  ba: { x: 360, y: 70 },
  architect: { x: 500, y: 70 },
  pm: { x: 640, y: 70 },
  dev: { x: 360, y: 180 },
  ux: { x: 500, y: 180 },
  security: { x: 640, y: 180 },
  qa: { x: 780, y: 180 },
  librarian: { x: 780, y: 70 },
  paused: { x: 920, y: 125 },
};

const els = {
  toastContainer: document.getElementById('toastContainer'),
  wsStatus: document.getElementById('wsStatus'),
  graphLoading: document.getElementById('graphLoading'),
  graphError: document.getElementById('graphError'),
  graphContainer: document.getElementById('graphContainer'),
  refreshGraphBtn: document.getElementById('refreshGraphBtn'),
  refreshTasksBtn: document.getElementById('refreshTasksBtn'),
  refreshRunsBtn: document.getElementById('refreshRunsBtn'),
  toggleTaskFormBtn: document.getElementById('toggleTaskFormBtn'),
  newTaskForm: document.getElementById('newTaskForm'),
  taskTitleInput: document.getElementById('taskTitleInput'),
  taskDescriptionInput: document.getElementById('taskDescriptionInput'),
  tasksLoading: document.getElementById('tasksLoading'),
  tasksBody: document.getElementById('tasksBody'),
  runsLoading: document.getElementById('runsLoading'),
  runsBody: document.getElementById('runsBody'),
  eventFeed: document.getElementById('eventFeed'),
  scrollLockToggle: document.getElementById('scrollLockToggle'),
  runDrawer: document.getElementById('runDrawer'),
  drawerTitle: document.getElementById('drawerTitle'),
  runMeta: document.getElementById('runMeta'),
  drawerControls: document.getElementById('drawerControls'),
  refreshRunDetailBtn: document.getElementById('refreshRunDetailBtn'),
  closeDrawerBtn: document.getElementById('closeDrawerBtn'),
  resultLoading: document.getElementById('resultLoading'),
  runResult: document.getElementById('runResult'),
  drawerEventsLoading: document.getElementById('drawerEventsLoading'),
  runEvents: document.getElementById('runEvents'),
  drawerArtifactsLoading: document.getElementById('drawerArtifactsLoading'),
  runArtifacts: document.getElementById('runArtifacts'),
};

function showToast(message) {
  const node = document.createElement('div');
  node.className = 'toast';
  node.textContent = message;
  els.toastContainer.appendChild(node);
  window.setTimeout(() => node.remove(), 4500);
}

function setLoading(el, on) {
  el.classList.toggle('hidden', !on);
}

function formatDate(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function statusBadge(status) {
  const cls = STATUS_CLASS[status] || '';
  return `<span class="status-badge ${cls}">${status || 'UNKNOWN'}</span>`;
}

async function apiFetch(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error(`Network error while calling ${path}: ${error.message}`);
  }
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch (_error) {
      // ignore
    }
    throw new Error(`${path} failed: ${detail}`);
  }
  return response.json();
}

function summarizePayload(payload) {
  if (!payload || typeof payload !== 'object') return String(payload);
  const entries = Object.entries(payload)
    .slice(0, 3)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`);
  return entries.join(' | ');
}

function addFeedEvent(eventType, payload) {
  const item = {
    ts: new Date().toISOString(),
    eventType,
    payload,
    summary: summarizePayload(payload),
  };
  state.feed.push(item);
  if (state.feed.length > MAX_FEED_EVENTS) state.feed.shift();
  renderFeed();
}

function renderFeed() {
  els.eventFeed.innerHTML = '';
  for (const event of state.feed) {
    const node = document.createElement('div');
    node.className = `event-item event-${(event.eventType || 'Unknown').replace(/[^a-zA-Z0-9_-]/g, '')}`;
    node.innerHTML = `
      <div><strong>${event.eventType}</strong></div>
      <div class="meta">${formatDate(event.ts)}</div>
      <div>${event.summary || ''}</div>
    `;
    els.eventFeed.appendChild(node);
  }
  if (state.autoScroll) {
    els.eventFeed.scrollTop = els.eventFeed.scrollHeight;
  }
}

function setWsStatus(kind, label) {
  els.wsStatus.classList.remove('connected', 'reconnecting', 'disconnected');
  els.wsStatus.classList.add(kind);
  const labelEl = els.wsStatus.querySelector('.label');
  if (labelEl) labelEl.textContent = label;
}

function wsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws/dashboard`;
}

function connectWebSocket() {
  if (state.ws) {
    state.ws.close();
    state.ws = null;
  }

  setWsStatus('reconnecting', state.wsRetries > 0 ? `Reconnecting (${state.wsRetries})` : 'Connecting');

  const ws = new WebSocket(wsUrl());
  state.ws = ws;

  ws.onopen = () => {
    state.wsRetries = 0;
    setWsStatus('connected', 'Connected');
    try {
      ws.send(JSON.stringify({ type: 'subscribe', channel: 'dashboard' }));
    } catch (_error) {
      // noop
    }
  };

  ws.onmessage = (message) => {
    let parsed;
    try {
      parsed = JSON.parse(message.data);
    } catch (_error) {
      return;
    }
    const eventType = parsed.type || parsed.event || 'Unknown';
    const payload = parsed.payload || {};
    addFeedEvent(eventType, payload);

    if (eventType === 'StateTransition' && payload.new_state) {
      state.transitionEvent = { old: payload.old_state, next: payload.new_state, at: Date.now() };
      applyStateTransition(payload.new_state);
      loadRuns(false);
    }
  };

  ws.onerror = () => {
    setWsStatus('disconnected', 'Disconnected');
  };

  ws.onclose = () => {
    if (state.ws !== ws) return;
    setWsStatus('disconnected', 'Disconnected');
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  if (state.wsReconnectTimer) return;
  state.wsRetries += 1;
  const delay = Math.min(
    MAX_RECONNECT_DELAY_MS,
    BASE_RECONNECT_DELAY_MS * Math.pow(2, Math.min(state.wsRetries, MAX_RETRY_EXPONENT))
  );
  setWsStatus('reconnecting', `Reconnecting in ${Math.round(delay / 1000)}s`);
  state.wsReconnectTimer = window.setTimeout(() => {
    state.wsReconnectTimer = null;
    connectWebSocket();
  }, delay);
}

function applyStateTransition(newState) {
  if (!state.graph) return;
  state.graph.currentState = newState;
  const currentNode = state.graph.nodes.find((node) => node.state === newState);
  state.graph.currentAgentId = currentNode ? currentNode.id : state.graph.currentAgentId;
  state.graph.nodes.forEach((node) => {
    node.isCurrent = currentNode ? node.id === currentNode.id : false;
  });
  state.graph.links.forEach((link) => {
    link.isActive = Array.isArray(link.states) && link.states.includes(newState);
  });
  renderGraph();
}

function renderGraph() {
  if (!state.graph) {
    els.graphContainer.innerHTML = '<div class="loading">No graph data yet.</div>';
    return;
  }

  const { nodes, links } = state.graph;
  const width = 1000;
  const height = 260;

  const defs = `
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto-start-reverse">
        <path d="M0,0 L10,4 L0,8 z" fill="#50668a"></path>
      </marker>
      <marker id="arrowActive" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto-start-reverse">
        <path d="M0,0 L10,4 L0,8 z" fill="#58beff"></path>
      </marker>
    </defs>
  `;

  const linkEls = links
    .map((link) => {
      const from = graphLayout[link.source];
      const to = graphLayout[link.target];
      if (!from || !to) return '';
      const marker = link.isActive ? 'url(#arrowActive)' : 'url(#arrow)';
      return `<line class="graph-link ${link.isActive ? 'active' : ''}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" marker-end="${marker}" />`;
    })
    .join('');

  const now = Date.now();
  const transitionFresh =
    state.transitionEvent && now - state.transitionEvent.at < TRANSITION_ANIMATION_DURATION_MS;

  const nodeEls = nodes
    .map((node) => {
      const pos = graphLayout[node.id];
      if (!pos) return '';
      const isTransition =
        transitionFresh &&
        state.transitionEvent &&
        (node.state === state.transitionEvent.old || node.state === state.transitionEvent.next);
      return `
      <g transform="translate(${pos.x}, ${pos.y})">
        <circle class="graph-node ${node.isCurrent ? 'current' : ''} ${isTransition ? 'transitioning' : ''}" r="29">
          <title>${node.description}</title>
        </circle>
        <text class="graph-label" y="4">${node.label}</text>
      </g>`;
    })
    .join('');

  els.graphContainer.innerHTML = `<svg class="graph-svg" viewBox="0 0 ${width} ${height}">${defs}${linkEls}${nodeEls}</svg>`;
}

async function loadGraph(showSpinner = true) {
  setLoading(els.graphLoading, showSpinner);
  els.graphError.classList.add('hidden');
  try {
    const payload = await apiFetch('/api/dashboard/agent-network');
    state.graph = payload;
    renderGraph();
  } catch (error) {
    els.graphError.textContent = error.message;
    els.graphError.classList.remove('hidden');
    showToast(`Agent graph error: ${error.message}`);
  } finally {
    setLoading(els.graphLoading, false);
  }
}

function renderTasks() {
  if (!state.tasks.length) {
    els.tasksBody.innerHTML = '<tr><td colspan="6">No tasks yet.</td></tr>';
    return;
  }

  const rows = [];
  for (const task of state.tasks) {
    const isExpanded = state.expandedTaskId === task.id;
    const isCreateRunOpen = state.createRunTaskId === task.id;
    rows.push(`
      <tr class="clickable" data-task-id="${task.id}">
        <td>${task.id}</td>
        <td>${escapeHtml(task.title)}</td>
        <td>${statusBadge(task.status)}</td>
        <td>${formatDate(task.created_at)}</td>
        <td>${(task.run_ids || []).length}</td>
        <td>
          <button class="btn small" data-action="toggle-runs" data-task-id="${task.id}">${isExpanded ? 'Hide' : 'Show'} Runs</button>
          <button class="btn small" data-action="toggle-create-run" data-task-id="${task.id}">${isCreateRunOpen ? 'Close' : 'Create Run'}</button>
        </td>
      </tr>
    `);

    if (isExpanded) {
      rows.push(`
        <tr>
          <td colspan="6">
            <div class="run-links">
              ${(task.run_ids || []).length
                ? task.run_ids
                    .map((id) => `<span class="run-link" data-action="open-run" data-run-id="${id}">${id}</span>`)
                    .join('')
                : '<span>No runs yet.</span>'}
            </div>
          </td>
        </tr>
      `);
    }

    if (isCreateRunOpen) {
      rows.push(`
        <tr>
          <td colspan="6">
            <form class="inline-form" data-action="create-run-form" data-task-id="${task.id}">
              <label>
                Max Steps: <span class="max-steps-value">8</span>
                <input type="range" min="1" max="50" value="8" name="max_steps" />
              </label>
              <div class="form-actions">
                <button class="btn primary" type="submit">Create Run</button>
              </div>
            </form>
          </td>
        </tr>
      `);
    }
  }

  els.tasksBody.innerHTML = rows.join('');
}

async function loadTasks(showSpinner = true) {
  setLoading(els.tasksLoading, showSpinner);
  try {
    const payload = await apiFetch('/api/hephaestus/tasks');
    state.tasks = payload.tasks || [];
    renderTasks();
  } catch (error) {
    showToast(`Tasks error: ${error.message}`);
  } finally {
    setLoading(els.tasksLoading, false);
  }
}

function runControlButtons(runId, status, compact = true) {
  const commands = ACTIVE_COMMANDS[status] || [];
  if (!commands.length) return '-';
  return commands
    .map(
      (command) =>
        `<button class="btn ${compact ? 'small' : ''}" data-action="run-control" data-run-id="${runId}" data-command="${command}">${command}</button>`
    )
    .join(' ');
}

function renderRuns() {
  if (!state.runs.length) {
    els.runsBody.innerHTML = '<tr><td colspan="8">No runs yet.</td></tr>';
    return;
  }

  els.runsBody.innerHTML = state.runs
    .map(
      (run) => `
      <tr class="clickable" data-action="open-run" data-run-id="${run.id}">
        <td>${run.id}</td>
        <td>${run.task_id}</td>
        <td>${statusBadge(run.status)}</td>
        <td>${run.current_state || '-'}</td>
        <td>${run.attempts ?? 0}</td>
        <td>${run.max_steps ?? '-'}</td>
        <td>${formatDate(run.updated_at)}</td>
        <td>${runControlButtons(run.id, run.status)}</td>
      </tr>
    `
    )
    .join('');
}

async function loadRuns(showSpinner = true) {
  setLoading(els.runsLoading, showSpinner);
  try {
    const payload = await apiFetch('/api/hephaestus/runs');
    state.runs = payload.runs || [];
    renderRuns();
    if (state.selectedRunId) {
      const current = state.runs.find((run) => run.id === state.selectedRunId);
      if (current) {
        state.selectedRun = current;
        renderDrawerMeta();
        renderDrawerControls();
      }
    }
  } catch (error) {
    showToast(`Runs error: ${error.message}`);
  } finally {
    setLoading(els.runsLoading, false);
  }
}

async function createTask(title, description) {
  await apiFetch('/api/hephaestus/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  });
  await loadTasks(false);
}

async function createRun(taskId, maxSteps) {
  await apiFetch('/api/hephaestus/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId, max_steps: maxSteps }),
  });
  await Promise.all([loadTasks(false), loadRuns(false)]);
}

async function controlRun(runId, command) {
  await apiFetch(`/api/hephaestus/runs/${runId}/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  await Promise.all([loadRuns(false), loadGraph(false)]);
  if (state.selectedRunId === runId) {
    await loadRunDetail(runId, false);
  }
}

function openRunDrawer(runId) {
  state.selectedRunId = runId;
  els.runDrawer.classList.add('open');
  els.runDrawer.setAttribute('aria-hidden', 'false');
  loadRunDetail(runId, true);
}

function closeRunDrawer() {
  state.selectedRunId = null;
  state.selectedRun = null;
  els.runDrawer.classList.remove('open');
  els.runDrawer.setAttribute('aria-hidden', 'true');
}

function renderDrawerMeta() {
  const run = state.selectedRun;
  if (!run) {
    els.drawerTitle.textContent = 'Run Details';
    els.runMeta.textContent = '';
    return;
  }

  els.drawerTitle.textContent = `Run ${run.id}`;
  els.runMeta.innerHTML = `
    Task: ${run.task_id}<br>
    Status: ${statusBadge(run.status)}<br>
    Current State: ${run.current_state || '-'}
  `;
}

function renderDrawerControls() {
  const run = state.selectedRun;
  if (!run) {
    els.drawerControls.innerHTML = '';
    return;
  }
  els.drawerControls.innerHTML = runControlButtons(run.id, run.status, false);
}

function renderResultSection(run, resultPayload) {
  const blocks = [];
  blocks.push(`status: ${resultPayload.status}`);
  blocks.push(`approved: ${resultPayload.approved ? 'yes' : 'no'}`);
  blocks.push(`commit_hash: ${resultPayload.commit_hash || '-'}`);
  blocks.push('result:\n' + JSON.stringify(resultPayload.result, null, 2));
  if (resultPayload.error) {
    blocks.push('error:\n' + JSON.stringify(resultPayload.error, null, 2));
  }
  if (run && run.error && !resultPayload.error) {
    blocks.push('run.error:\n' + JSON.stringify(run.error, null, 2));
  }
  els.runResult.textContent = blocks.join('\n\n');
}

function renderEventsSection(events) {
  if (!events.length) {
    els.runEvents.innerHTML = '<div class="list-item">No events.</div>';
    return;
  }
  const ordered = [...events].reverse();
  els.runEvents.innerHTML = ordered
    .map((event) => {
      const eventType = event.event || event.type || 'Event';
      const payload = event.payload !== undefined ? event.payload : event;
      const ts = event.timestamp || event.created_at || event.ts || null;
      return `<div class="list-item"><strong>${escapeHtml(String(eventType))}</strong> <span class="meta">${formatDate(ts)}</span><br><code>${escapeHtml(
        JSON.stringify(payload, null, 2)
      )}</code></div>`;
    })
    .join('');
}

function renderArtifactsSection(artifacts) {
  if (!artifacts.length) {
    els.runArtifacts.innerHTML = '<div class="list-item">No artifacts.</div>';
    return;
  }
  els.runArtifacts.innerHTML = artifacts
    .map((artifact) => `<div class="list-item"><code>${escapeHtml(JSON.stringify(artifact, null, 2))}</code></div>`)
    .join('');
}

async function loadRunDetail(runId, showSpinner = true) {
  setLoading(els.resultLoading, showSpinner);
  setLoading(els.drawerEventsLoading, showSpinner);
  setLoading(els.drawerArtifactsLoading, showSpinner);

  try {
    const [runPayload, resultPayload, eventsPayload, artifactsPayload] = await Promise.all([
      apiFetch(`/api/hephaestus/runs/${runId}`),
      apiFetch(`/api/hephaestus/runs/${runId}/result`),
      apiFetch(`/api/hephaestus/runs/${runId}/events`),
      apiFetch(`/api/hephaestus/runs/${runId}/artifacts`),
    ]);

    state.selectedRun = runPayload.run;
    renderDrawerMeta();
    renderDrawerControls();
    renderResultSection(runPayload.run, resultPayload);
    renderEventsSection(eventsPayload.events || []);
    renderArtifactsSection(artifactsPayload.artifacts || []);
  } catch (error) {
    showToast(`Run detail error: ${error.message}`);
  } finally {
    setLoading(els.resultLoading, false);
    setLoading(els.drawerEventsLoading, false);
    setLoading(els.drawerArtifactsLoading, false);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function bindEvents() {
  els.refreshGraphBtn.addEventListener('click', () => loadGraph(true));
  els.refreshTasksBtn.addEventListener('click', () => loadTasks(true));
  els.refreshRunsBtn.addEventListener('click', () => loadRuns(true));

  els.toggleTaskFormBtn.addEventListener('click', () => {
    els.newTaskForm.classList.toggle('hidden');
  });

  els.newTaskForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const title = els.taskTitleInput.value.trim();
    const description = els.taskDescriptionInput.value.trim();
    if (!title) {
      showToast('Task title is required.');
      return;
    }
    try {
      await createTask(title, description);
      els.taskTitleInput.value = '';
      els.taskDescriptionInput.value = '';
      els.newTaskForm.classList.add('hidden');
    } catch (error) {
      showToast(`Create task failed: ${error.message}`);
    }
  });

  els.tasksBody.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const action = target.dataset.action;

    if (action === 'toggle-runs') {
      state.expandedTaskId = state.expandedTaskId === target.dataset.taskId ? null : target.dataset.taskId;
      renderTasks();
      return;
    }

    if (action === 'toggle-create-run') {
      state.createRunTaskId = state.createRunTaskId === target.dataset.taskId ? null : target.dataset.taskId;
      renderTasks();
      return;
    }

    if (action === 'open-run') {
      openRunDrawer(target.dataset.runId);
      return;
    }

    const taskRow = target.closest('tr[data-task-id]');
    if (taskRow instanceof HTMLElement && taskRow.dataset.taskId) {
      state.expandedTaskId = state.expandedTaskId === taskRow.dataset.taskId ? null : taskRow.dataset.taskId;
      renderTasks();
    }
  });

  els.tasksBody.addEventListener('input', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.name === 'max_steps') {
      const holder = target.closest('label')?.querySelector('.max-steps-value');
      if (holder) holder.textContent = target.value;
    }
  });

  els.tasksBody.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.dataset.action !== 'create-run-form') return;
    event.preventDefault();

    const taskId = form.dataset.taskId;
    const slider = form.querySelector('input[name="max_steps"]');
    const maxSteps = slider instanceof HTMLInputElement ? Number(slider.value) : 8;

    try {
      await createRun(taskId, maxSteps);
      state.createRunTaskId = null;
      renderTasks();
    } catch (error) {
      showToast(`Create run failed: ${error.message}`);
    }
  });

  els.runsBody.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    const action = target.dataset.action;
    if (action === 'run-control') {
      event.stopPropagation();
      const runId = target.dataset.runId;
      const command = target.dataset.command;
      try {
        await controlRun(runId, command);
      } catch (error) {
        showToast(`Control failed: ${error.message}`);
      }
      return;
    }

    const row = target.closest('[data-action="open-run"]');
    if (row instanceof HTMLElement && row.dataset.runId) {
      openRunDrawer(row.dataset.runId);
    }
  });

  els.drawerControls.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.dataset.action !== 'run-control') return;

    try {
      await controlRun(target.dataset.runId, target.dataset.command);
    } catch (error) {
      showToast(`Control failed: ${error.message}`);
    }
  });

  els.refreshRunDetailBtn.addEventListener('click', () => {
    if (state.selectedRunId) {
      loadRunDetail(state.selectedRunId, true);
    }
  });

  els.closeDrawerBtn.addEventListener('click', closeRunDrawer);

  els.scrollLockToggle.addEventListener('change', () => {
    state.autoScroll = Boolean(els.scrollLockToggle.checked);
  });
}

async function bootstrap() {
  bindEvents();
  await Promise.all([loadGraph(true), loadTasks(true), loadRuns(true)]);

  if (state.runAutoRefresh) {
    window.clearInterval(state.runAutoRefresh);
  }
  state.runAutoRefresh = window.setInterval(() => {
    loadRuns(false);
  }, 5000);

  connectWebSocket();
}

bootstrap().catch((error) => {
  showToast(`Initialization failed: ${error.message}`);
});
