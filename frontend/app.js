const apiBase = "/api";

let accessToken = null;
let currentUser = null;
let currentPage = 1;
let pageSize = 10;
let currentTicket = null;

const $ = (id) => document.getElementById(id);

function clearTicketSelection() {
  currentTicket = null;
  document
    .querySelectorAll("#tickets-body tr")
    .forEach((tr) => tr.classList.remove("active-row"));
  setHidden($("ticket-detail-content"), true);
  setHidden($("ticket-empty"), false);
}

function resetFilters() {
  $("filter-status").value = "";
  $("filter-priority").value = "";
  $("filter-search").value = "";
}

function selectTicketInTable(ticketId) {
  const row = document.querySelector(`#tickets-body tr[data-id="${ticketId}"]`);
  if (!row) return false;
  row.scrollIntoView({ block: "center", behavior: "smooth" });
  row.click();
  return true;
}

function setHidden(el, hidden) {
  if (!el) return;
  if (hidden) el.classList.add("hidden");
  else el.classList.remove("hidden");
}

function showToast(message, type = "success") {
  const toast = $("global-toast");
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setHidden(toast, false);
  setTimeout(() => setHidden(toast, true), 2500);
}

function setGlobalLoading(visible) {
  setHidden($("global-loading"), !visible);
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  if (!(options.body instanceof FormData) && !headers["Content-Type"] && options.method && options.method !== "GET") {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  });
  if (resp.status === 401) {
    logout();
    throw new Error("Sesión expirada. Inicia sesión de nuevo.");
  }
  let data = null;
  const text = await resp.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!resp.ok) {
    const detail = data && data.detail ? data.detail : "Error en la petición";
    throw new Error(detail);
  }
  return data;
}

function saveToken(token) {
  accessToken = token;
  localStorage.setItem("accessToken", token);
}

function loadTokenFromStorage() {
  const token = localStorage.getItem("accessToken");
  if (token) {
    accessToken = token;
    return true;
  }
  return false;
}

function logout() {
  accessToken = null;
  currentUser = null;
  localStorage.removeItem("accessToken");
  setHidden($("dashboard-view"), true);
  setHidden($("login-view"), false);
  setHidden($("user-info"), true);
  clearTicketSelection();
}

async function handleLogin(e) {
  e.preventDefault();
  const email = $("email").value.trim();
  const password = $("password").value;
  setHidden($("login-error"), true);
  setGlobalLoading(true);
  try {
    const body = JSON.stringify({ email, password });
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body,
    });
    saveToken(data.access_token);
    await loadCurrentUser();
    $("password").value = "";
    setHidden($("login-view"), true);
    setHidden($("dashboard-view"), false);
    resetFilters();
    await loadTickets();
    showToast("Sesión iniciada", "success");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const el = $("login-error");
    el.textContent = msg;
    setHidden(el, false);
  } finally {
    setGlobalLoading(false);
  }
}

async function loadCurrentUser() {
  const me = await apiFetch("/auth/me");
  currentUser = me;
  $("user-email").textContent = me.email;
  $("user-role").textContent = me.role;
  $("user-role").classList.add(`badge-role-${me.role}`);
  setHidden($("user-info"), false);
  const createBtn = $("create-ticket-btn");
   const exportBtn = $("export-tickets-btn");
  if (me.role === "USER") {
    createBtn.style.display = "inline-flex";
    exportBtn.style.display = "none";
    $("tickets-title").textContent = "Mis tickets";
  } else {
    createBtn.style.display = "none";
    exportBtn.style.display = "inline-flex";
    $("tickets-title").textContent = "Todos los tickets";
  }
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("es-ES");
}

async function loadTickets(pageArg) {
  if (pageArg) {
    currentPage = pageArg;
  }
  setHidden($("tickets-loading"), false);
  const status = $("filter-status").value || "";
  const priority = $("filter-priority").value || "";
  const search = $("filter-search").value.trim();
  const params = new URLSearchParams();
  params.set("page", String(currentPage));
  params.set("page_size", String(pageSize));
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  if (search) params.set("search", search);
  try {
    const data = await apiFetch(`/tickets?${params.toString()}`);
    renderTickets(data);
  } catch (err) {
    showToast(err.message || "Error cargando tickets", "error");
  } finally {
    setHidden($("tickets-loading"), true);
  }
}

function renderTickets(result) {
  const tbody = $("tickets-body");
  tbody.innerHTML = "";
  result.items.forEach((t) => {
    const tr = document.createElement("tr");
    tr.dataset.id = t.id;
    tr.innerHTML = `
      <td>${t.id}</td>
      <td>${t.title}</td>
      <td><span class="badge priority-${t.priority}">${t.priority}</span></td>
      <td><span class="badge status-${t.status}">${t.status}</span></td>
      <td>${formatDate(t.created_at)}</td>
      <td>${t.assigned_to_id ?? "-"}</td>
    `;
    tr.addEventListener("click", () => selectTicketRow(tr, t.id));
    tbody.appendChild(tr);
  });

  $("page-info").textContent = `Página ${result.page} (${result.items.length} de ${result.total})`;
  $("page-prev").disabled = result.page <= 1;
  $("page-next").disabled = result.page * result.page_size >= result.total;
}

async function selectTicketRow(row, ticketId) {
  document
    .querySelectorAll("#tickets-body tr")
    .forEach((tr) => tr.classList.remove("active-row"));
  row.classList.add("active-row");
  await loadTicketDetail(ticketId);
  await loadComments(ticketId);
}

async function loadTicketDetail(ticketId) {
  setHidden($("ticket-empty"), true);
  setHidden($("ticket-detail-content"), false);
  try {
    const t = await apiFetch(`/tickets/${ticketId}`);
    currentTicket = t;
    $("ticket-title").textContent = t.title;
    $("ticket-description").textContent = t.description;
    const priorityEl = $("ticket-priority");
    priorityEl.textContent = t.priority;
    priorityEl.className = `badge priority-${t.priority}`;
    const statusEl = $("ticket-status");
    statusEl.textContent = t.status;
    statusEl.className = `badge status-${t.status}`;
    $("ticket-created-by").textContent = t.created_by_email || t.created_by_id;
    $("ticket-assigned-to").textContent = t.assigned_to_email || (t.assigned_to_id ?? "-");

    if (currentUser.role === "AGENT") {
      setHidden($("ticket-edit-agent"), false);
      $("edit-status").value = t.status;
      $("edit-priority").value = t.priority;
    } else {
      setHidden($("ticket-edit-agent"), true);
    }
  } catch (err) {
    showToast(err.message || "Error cargando ticket", "error");
  }
}

async function loadComments(ticketId) {
  setHidden($("comments-loading"), false);
  const list = $("comments-list");
  list.innerHTML = "";
  try {
    const items = await apiFetch(`/tickets/${ticketId}/comments`);
    items.forEach((c) => {
      const div = document.createElement("div");
      div.className = "comment-item";
      const authorLabel = (c.author_email && c.author_email.includes("agent")) ? "Agente" : "Usuario";
      div.innerHTML = `
        <div class="comment-meta">
          <span class="comment-author">${authorLabel}: ${c.author_email || "—"}</span>
          <span>${formatDate(c.created_at)}</span>
        </div>
        <div class="comment-content">${c.content}</div>
      `;
      list.appendChild(div);
    });
  } catch (err) {
    showToast(err.message || "Error cargando comentarios", "error");
  } finally {
    setHidden($("comments-loading"), true);
  }
}

async function handleSaveAgentEdit() {
  if (!currentTicket) return;
  // Solo se guardan cambios si se pulsa explícitamente este botón.
  const payload = {
    status: $("edit-status").value,
    priority: $("edit-priority").value,
  };
  try {
    const updated = await apiFetch(`/tickets/${currentTicket.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    currentTicket = updated;
    showToast("Ticket actualizado", "success");
    await loadTickets(currentPage);
    await loadTicketDetail(currentTicket.id);
  } catch (err) {
    showToast(err.message || "Error actualizando ticket", "error");
  }
}

async function handleAssignToMe() {
  if (!currentTicket || !currentUser || currentUser.role !== "AGENT") return;
  // Este botón solo debe asignar el ticket al agente,
  // sin guardar otros cambios que pueda haber en los selectores.
  const payload = {
    assigned_to_id: currentUser.id,
  };
  try {
    const updated = await apiFetch(`/tickets/${currentTicket.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    currentTicket = updated;
    showToast("Ticket asignado a ti", "success");
    await loadTickets(currentPage);
    await loadTicketDetail(currentTicket.id);
  } catch (err) {
    showToast(err.message || "Error asignando ticket", "error");
  }
}

async function handleDeleteTicket() {
  if (!currentTicket) return;
  if (!confirm("¿Seguro que quieres eliminar este ticket?")) return;
  try {
    await apiFetch(`/tickets/${currentTicket.id}`, { method: "DELETE" });
    showToast("Ticket eliminado", "success");
    clearTicketSelection();
    await loadTickets();
  } catch (err) {
    showToast(err.message || "Error eliminando ticket", "error");
  }
}

async function handleAddComment() {
  if (!currentTicket) return;
  const content = $("new-comment").value.trim();
  if (!content) {
    showToast("Escribe un comentario", "error");
    return;
  }
  try {
    await apiFetch(`/tickets/${currentTicket.id}/comments`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    $("new-comment").value = "";
    await loadComments(currentTicket.id);
    showToast("Comentario añadido", "success");
  } catch (err) {
    showToast(err.message || "Error añadiendo comentario", "error");
  }
}

async function handleExportTickets() {
  try {
    setGlobalLoading(true);
    const headers = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }
    const resp = await fetch(`${apiBase}/tickets/export`, {
      method: "GET",
      headers,
    });
    if (!resp.ok) {
      const text = await resp.text();
      let message = "Error exportando tickets";
      try {
        const data = JSON.parse(text);
        if (data && data.detail) {
          message = data.detail;
        }
      } catch {
        // texto plano
      }
      throw new Error(message);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `tickets_${date}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("Exportación iniciada (revisa tus descargas).", "success");
  } catch (err) {
    showToast(err.message || "Error exportando tickets", "error");
  } finally {
    setGlobalLoading(false);
  }
}

function openCreateModal() {
  $("new-title").value = "";
  $("new-description").value = "";
  $("new-priority").value = "MEDIUM";
  setHidden($("create-ticket-error"), true);
  setHidden($("create-ticket-modal"), false);
}

function closeCreateModal() {
  setHidden($("create-ticket-modal"), true);
}

async function handleCreateTicket() {
  const title = $("new-title").value.trim();
  const description = $("new-description").value.trim();
  const priority = $("new-priority").value;
  const errorEl = $("create-ticket-error");
  setHidden(errorEl, true);
  if (!title || !description) {
    errorEl.textContent = "Título y descripción son obligatorios.";
    setHidden(errorEl, false);
    return;
  }
  try {
    const ticket = await apiFetch("/tickets", {
      method: "POST",
      body: JSON.stringify({ title, description, priority }),
    });
    closeCreateModal();
    showToast("Ticket creado. Aparece en el listado.", "success");

    resetFilters();
    await loadTickets(1);

    // Opcional: resaltar la fila del nuevo ticket sin abrir el panel
    const row = document.querySelector(`#tickets-body tr[data-id="${ticket.id}"]`);
    if (row) {
      row.scrollIntoView({ block: "center", behavior: "smooth" });
      row.classList.add("highlight-new");
      setTimeout(() => row.classList.remove("highlight-new"), 2000);
    }
  } catch (err) {
    errorEl.textContent = err.message || "Error creando ticket";
    setHidden(errorEl, false);
  }
}

function initEvents() {
  $("login-form").addEventListener("submit", handleLogin);
  $("logout-btn").addEventListener("click", logout);
  $("close-detail-btn").addEventListener("click", clearTicketSelection);
  $("filter-apply").addEventListener("click", () => loadTickets(1));
  $("page-prev").addEventListener("click", () => {
    if (currentPage > 1) loadTickets(currentPage - 1);
  });
  $("page-next").addEventListener("click", () => loadTickets(currentPage + 1));
  $("save-agent-edit").addEventListener("click", handleSaveAgentEdit);
  $("assign-to-me").addEventListener("click", handleAssignToMe);
  $("delete-ticket").addEventListener("click", handleDeleteTicket);
  $("add-comment").addEventListener("click", handleAddComment);
  $("export-tickets-btn").addEventListener("click", handleExportTickets);
  $("create-ticket-btn").addEventListener("click", openCreateModal);
  $("close-modal").addEventListener("click", closeCreateModal);
  $("create-ticket-cancel").addEventListener("click", closeCreateModal);
  $("create-ticket-submit").addEventListener("click", handleCreateTicket);
}

async function bootstrap() {
  initEvents();
  if (loadTokenFromStorage()) {
    try {
      setGlobalLoading(true);
      await loadCurrentUser();
      setHidden($("login-view"), true);
      setHidden($("dashboard-view"), false);
      resetFilters();
      await loadTickets();
    } catch {
      logout();
    } finally {
      setGlobalLoading(false);
    }
  } else {
    setHidden($("login-view"), false);
  }
}

window.addEventListener("DOMContentLoaded", bootstrap);

