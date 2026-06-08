const zkStateEl = document.getElementById('zk-state');
const nodeExistsEl = document.getElementById('node-exists');
const childCountEl = document.getElementById('child-count');
const externalAppEl = document.getElementById('external-app');
const treeEl = document.getElementById('tree');
const eventLogEl = document.getElementById('event-log');
const toastContainer = document.getElementById('toast-container');

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'state') {
      updateState(data.payload);
    } else if (data.type === 'notification') {
      showToast(data.message);
      if (typeof data.childCount === 'number') {
        childCountEl.textContent = data.childCount;
      }
      addLogEntry(data.message);
    } else if (data.type === 'log') {
      addLogEntry(data.message);
    }
  };

  ws.onclose = () => {
    addLogEntry('WebSocket disconnected — reconnecting in 2s...');
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = () => ws.close();
}

function updateState(state) {
  const conn = state.zkConnectionState || 'DISCONNECTED';
  zkStateEl.textContent = conn;
  zkStateEl.className = 'badge ' + (conn === 'CONNECTED' ? 'connected' : 'disconnected');

  nodeExistsEl.textContent = state.nodeAExists ? 'EXISTS' : 'ABSENT';
  nodeExistsEl.className = 'badge ' + (state.nodeAExists ? 'exists' : 'absent');

  childCountEl.textContent = state.childCount ?? 0;

  externalAppEl.textContent = state.externalAppRunning ? 'RUNNING' : 'STOPPED';
  externalAppEl.className = 'badge ' + (state.externalAppRunning ? 'running' : 'stopped');

  renderTree(state.tree);
}

function renderTree(tree) {
  if (!tree) {
    treeEl.className = 'tree empty';
    treeEl.textContent = 'Znode /a does not exist yet.';
    return;
  }
  treeEl.className = 'tree';
  treeEl.innerHTML = renderNode(tree);
}

function renderNode(node) {
  const data = node.data ? ` <span class="node-data">[${escapeHtml(node.data)}]</span>` : '';
  let html = `<span class="node-name">${escapeHtml(node.name)}</span>${data}`;
  if (node.children && node.children.length > 0) {
    html += '<ul>';
    for (const child of node.children) {
      html += `<li>${renderNode(child)}</li>`;
    }
    html += '</ul>';
  }
  return html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function addLogEntry(message) {
  const li = document.createElement('li');
  const time = new Date().toLocaleTimeString();
  li.textContent = `[${time}] ${message}`;
  eventLogEl.prepend(li);
  while (eventLogEl.children.length > 50) {
    eventLogEl.removeChild(eventLogEl.lastChild);
  }
}

fetch('/api/state')
  .then((r) => r.json())
  .then(updateState)
  .catch(() => addLogEntry('Failed to load initial state'));

connectWebSocket();
