// FlowDesk SPA: auth gate, dashboard, projects, kanban board with
// drag & drop, and a task drawer with comments. All data comes from the
// REST API via js/api.js — there is no local mock state.
import { api, getToken, setToken, ApiError } from "./api.js";

const STATUSES = [
  ["todo", "未着手"],
  ["in_progress", "進行中"],
  ["review", "レビュー"],
  ["done", "完了"],
];
const PRIO_LABEL = { low: "低", medium: "中", high: "高", urgent: "緊急" };

const state = { user: null, projects: [], boardProjectId: null, drawerTaskId: null };
const $ = (sel) => document.querySelector(sel);

// ---------- auth ----------
let authMode = "login";
function setAuthMode(mode) {
  authMode = mode;
  $("#authName").hidden = mode === "login";
  $("#tabLogin").classList.toggle("active", mode === "login");
  $("#tabRegister").classList.toggle("active", mode === "register");
  $("#authSubmit").textContent = mode === "login" ? "ログイン" : "登録してはじめる";
  $("#authError").textContent = "";
}
$("#tabLogin").addEventListener("click", () => setAuthMode("login"));
$("#tabRegister").addEventListener("click", () => setAuthMode("register"));

async function onAuthed(token, user) {
  setToken(token);
  state.user = user;
  $("#authView").hidden = true;
  $("#appView").hidden = false;
  $("#currentUser").textContent = user.name;
  await refreshProjects();
  showView("dashboard");
  await renderDashboard();
}

$("#authForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = $("#authEmail").value.trim();
  const password = $("#authPassword").value;
  try {
    const res =
      authMode === "login"
        ? await api.login(email, password)
        : await api.register($("#authName").value.trim(), email, password);
    await onAuthed(res.access_token, res.user);
  } catch (err) {
    $("#authError").textContent =
      err instanceof ApiError ? err.message : "通信に失敗しました";
  }
});

$("#demoLogin").addEventListener("click", async () => {
  try {
    const res = await api.login("demo@flowdesk.dev", "demo-password");
    await onAuthed(res.access_token, res.user);
  } catch {
    $("#authError").textContent = "デモデータが未投入です。サーバーで python -m app.seed を実行してください。";
  }
});

$("#logoutBtn").addEventListener("click", () => {
  setToken(null);
  state.user = null;
  $("#appView").hidden = true;
  $("#authView").hidden = false;
});

// ---------- navigation ----------
function showView(name) {
  for (const v of ["dashboard", "projects", "board"]) {
    $(`#view-${v}`).hidden = v !== name;
  }
  document.querySelectorAll(".nav-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.nav === name)
  );
  if (name === "dashboard") renderDashboard();
  if (name === "projects") renderProjects();
  if (name === "board") renderBoard();
}
document.querySelectorAll(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => showView(b.dataset.nav))
);

// ---------- dashboard ----------
async function renderDashboard() {
  const d = await api.dashboard();
  const byStatus = d.tasks_by_status || {};
  const open = Object.entries(byStatus)
    .filter(([s]) => s !== "done")
    .reduce((sum, [, n]) => sum + n, 0);
  $("#kpiProjects").textContent = d.project_count;
  $("#kpiOpen").textContent = open;
  $("#kpiOverdue").textContent = d.overdue_count;
  $("#kpiMine").textContent = d.assigned_to_me;

  $("#projectProgress").innerHTML = d.projects.length
    ? ""
    : "<p class='muted'>プロジェクトがありません。</p>";
  for (const p of d.projects) {
    const pct = p.task_count ? Math.round((100 * (p.done_count || 0)) / p.task_count) : 0;
    const row = document.createElement("div");
    row.className = "progress-row";
    row.innerHTML = `<div>${escapeHtml(p.name)} <span class="muted small">${p.done_count || 0}/${p.task_count} 完了</span></div>
      <div class="bar"><div class="fill" style="width:${pct}%"></div></div>`;
    $("#projectProgress").appendChild(row);
  }

  const list = $("#activityList");
  list.innerHTML = "";
  for (const a of d.recent_activity) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(a.user_name)}</strong> — ${escapeHtml(a.action)}
      <span class="muted">${escapeHtml(a.detail)}</span>
      <div class="when">${escapeHtml(a.project_name)} ・ ${escapeHtml(a.created_at)}</div>`;
    list.appendChild(li);
  }
}

// ---------- projects ----------
async function refreshProjects() {
  state.projects = await api.listProjects();
  const select = $("#boardProjectSelect");
  select.innerHTML = "";
  for (const p of state.projects) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    select.appendChild(opt);
  }
  if (!state.boardProjectId && state.projects.length) {
    state.boardProjectId = state.projects[0].id;
  }
  select.value = state.boardProjectId ?? "";
}

function renderProjects() {
  const grid = $("#projectGrid");
  grid.innerHTML = "";
  for (const p of state.projects) {
    const card = document.createElement("button");
    card.className = "project-card";
    const pct = p.task_count ? Math.round((100 * p.done_count) / p.task_count) : 0;
    card.innerHTML = `<h3>${escapeHtml(p.name)}</h3>
      <p class="muted">${escapeHtml(p.description || "")}</p>
      <p class="muted small">タスク ${p.task_count} 件 ／ 完了 ${p.done_count} 件（${pct}%）</p>`;
    card.addEventListener("click", () => {
      state.boardProjectId = p.id;
      $("#boardProjectSelect").value = String(p.id);
      showView("board");
    });
    grid.appendChild(card);
  }
}

$("#projectForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api.createProject($("#projectName").value.trim(), $("#projectDesc").value.trim());
  $("#projectName").value = "";
  $("#projectDesc").value = "";
  await refreshProjects();
  renderProjects();
});

$("#boardProjectSelect").addEventListener("change", (e) => {
  state.boardProjectId = Number(e.target.value);
  renderBoard();
});

// ---------- board ----------
async function renderBoard() {
  const board = $("#board");
  board.innerHTML = "";
  const project = state.projects.find((p) => p.id === state.boardProjectId);
  $("#boardTitle").textContent = project ? `${project.name} のボード` : "ボード";
  if (!project) {
    board.innerHTML = "<p class='muted'>プロジェクトを作成するとボードが使えます。</p>";
    return;
  }
  const tasks = await api.listTasks(project.id);
  for (const [status, label] of STATUSES) {
    const col = document.createElement("div");
    col.className = "column";
    col.dataset.status = status;
    const inCol = tasks.filter((t) => t.status === status);
    col.innerHTML = `<h4>${label} <span class="muted">${inCol.length}</span></h4>`;
    for (const t of inCol) col.appendChild(taskCard(t));
    col.addEventListener("dragover", (e) => {
      e.preventDefault();
      col.classList.add("drag-over");
    });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async (e) => {
      e.preventDefault();
      col.classList.remove("drag-over");
      const taskId = Number(e.dataTransfer.getData("text/plain"));
      if (taskId) {
        await api.updateTask(taskId, { status });
        renderBoard();
      }
    });
    board.appendChild(col);
  }
}

function taskCard(t) {
  const el = document.createElement("div");
  el.className = "task-card";
  el.draggable = true;
  el.innerHTML = `<div class="title">${escapeHtml(t.title)}</div>
    <div class="meta">
      <span class="prio prio-${t.priority}">${PRIO_LABEL[t.priority]}</span>
      ${t.assignee_name ? `<span>担当: ${escapeHtml(t.assignee_name)}</span>` : ""}
      ${t.due_date ? `<span>期限: ${escapeHtml(t.due_date)}</span>` : ""}
      <span>コメント ${t.comment_count}</span>
    </div>`;
  el.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", String(t.id)));
  el.addEventListener("click", () => openDrawer(t));
  return el;
}

$("#taskForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.boardProjectId) return;
  const due = $("#taskDue").value || null;
  await api.createTask(state.boardProjectId, {
    title: $("#taskTitle").value.trim(),
    priority: $("#taskPriority").value,
    due_date: due,
  });
  $("#taskTitle").value = "";
  renderBoard();
});

// ---------- task drawer ----------
async function openDrawer(task) {
  state.drawerTaskId = task.id;
  $("#drawerTitle").textContent = task.title;
  $("#drawerDesc").textContent = task.description || "（説明なし）";
  $("#drawerMeta").textContent =
    `優先度: ${PRIO_LABEL[task.priority]} ／ 作成: ${task.creator_name}` +
    (task.assignee_name ? ` ／ 担当: ${task.assignee_name}` : "") +
    (task.due_date ? ` ／ 期限: ${task.due_date}` : "");
  $("#drawerStatus").value = task.status;
  $("#taskDrawer").hidden = false;
  await renderComments();
}

async function renderComments() {
  const comments = await api.listComments(state.drawerTaskId);
  const list = $("#commentList");
  list.innerHTML = "";
  for (const c of comments) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(c.author_name)}</strong> ${escapeHtml(c.body)}
      <div class="when">${escapeHtml(c.created_at)}</div>`;
    list.appendChild(li);
  }
}

$("#drawerStatus").addEventListener("change", async (e) => {
  await api.updateTask(state.drawerTaskId, { status: e.target.value });
  renderBoard();
});
$("#drawerClose").addEventListener("click", () => {
  $("#taskDrawer").hidden = true;
});
$("#commentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api.addComment(state.drawerTaskId, $("#commentBody").value.trim());
  $("#commentBody").value = "";
  renderComments();
});

// ---------- boot ----------
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

(async function boot() {
  if (!getToken()) return;
  try {
    const user = await api.me();
    await onAuthed(getToken(), user);
  } catch {
    setToken(null);
  }
})();
