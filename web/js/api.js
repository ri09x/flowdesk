// FlowDesk API client: the single place that knows about fetch, the base
// URL, the JWT header, and API error shapes. Views never call fetch directly.
const TOKEN_KEY = "flowdesk.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `API error ${status}`);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data.detail);
  return data;
}

export const api = {
  register: (name, email, password) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }),
  login: (email, password) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request("/api/auth/me"),
  dashboard: () => request("/api/dashboard"),
  listProjects: () => request("/api/projects"),
  createProject: (name, description) =>
    request("/api/projects", { method: "POST", body: JSON.stringify({ name, description }) }),
  getProject: (id) => request(`/api/projects/${id}`),
  listTasks: (projectId, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/api/projects/${projectId}/tasks${qs ? "?" + qs : ""}`);
  },
  createTask: (projectId, payload) =>
    request(`/api/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (taskId, payload) =>
    request(`/api/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listComments: (taskId) => request(`/api/tasks/${taskId}/comments`),
  addComment: (taskId, body) =>
    request(`/api/tasks/${taskId}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
};
