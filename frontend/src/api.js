const BASE = '/api'

async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      /* cuerpo no JSON */
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const STREAM_URL = `${BASE}/camera/stream`

export const api = {
  generatePlan: (profile) => request('/plan', { method: 'POST', body: profile }),
  startCamera: (plan, source) =>
    request(`/camera/start${source ? `?source=${encodeURIComponent(source)}` : ''}`, {
      method: 'POST',
      body: { plan },
    }),
  calibrate: () => request('/camera/calibrate', { method: 'POST' }),
  next: () => request('/camera/next', { method: 'POST' }),
  stop: () => request('/camera/stop', { method: 'POST' }),
  getState: () => request('/camera/state'),
}
