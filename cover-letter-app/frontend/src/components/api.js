/**
 * api.js
 * ──────
 * Все HTTP-запросы к FastAPI в одном месте.
 * В dev-режиме Vite проксирует /api/* на localhost:8080.
 */

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Tasks ──────────────────────────────────────────────────────────────────

export const getTasks = (search = "") =>
  request(`/tasks${search ? `?search=${encodeURIComponent(search)}` : ""}`);

export const getTask = (taskId) =>
  request(`/tasks/${taskId}`);

export const addTask = ({ vacancy_url, vacancy_text }) =>
  request("/tasks", {
    method: "POST",
    body: JSON.stringify({ vacancy_url: vacancy_url || null, vacancy_text: vacancy_text || null }),
  });

export const regenerateTask = (taskId) =>
  request(`/tasks/${taskId}/regenerate`, { method: "POST" });

export const deleteTask = (taskId) =>
  request(`/tasks/${taskId}`, { method: "DELETE" });

// ── Files ──────────────────────────────────────────────────────────────────

export const getLetter = (taskId) =>
  request(`/tasks/${taskId}/letter`);

export const getAllFiles = (taskId) =>
  request(`/tasks/${taskId}/files`);
