/** 后端接口封装。开发时经 Vite proxy 转发到 FastAPI。 */

import type {
  AnswerPayload,
  LibraryPayload,
  SemesterMeta,
  SettingsPayload,
  StreamEvent,
  WeekView,
} from './types'

const BASE = '/api'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* 非 JSON 错误体，保持状态码 */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

function jsonBody(data: unknown): RequestInit {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

export const api = {
  // ---- 设置 ----
  getSettings: () => req<SettingsPayload>('/settings'),
  putSettings: (data: { base_url: string; api_key: string; model: string }) =>
    req<{ ok: boolean; message: string }>('/settings', { method: 'PUT', ...jsonBody(data) }),
  clearSettings: () =>
    req<{ ok: boolean; message: string }>('/settings/clear', { method: 'POST' }),

  // ---- 资料库 ----
  getLibrary: () => req<LibraryPayload>('/library'),
  deleteDoc: (docId: string) =>
    req<{ ok: boolean }>(`/library/${encodeURIComponent(docId)}`, { method: 'DELETE' }),
  uploadPdf: async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return req<{ doc_id: string; doc_name: string; pages: number; chunks: number }>(
      '/library/upload',
      { method: 'POST', body: fd },
    )
  },

  // ---- 问答 ----
  ask: (question: string) =>
    req<AnswerPayload>('/ask', { method: 'POST', ...jsonBody({ question }) }),

  /** 流式问答：逐条回调事件，返回一个可用于中断的 AbortController。 */
  askStream(
    question: string,
    onEvent: (ev: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    return (async () => {
      const res = await fetch(BASE + '/ask/stream', {
        method: 'POST',
        ...jsonBody({ question }),
        signal,
      })
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })

        // SSE 以空行分隔事件
        let idx: number
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const line = chunk.trim()
          if (!line.startsWith('data:')) continue
          const payload = line.slice(5).trim()
          if (payload === '[DONE]') return
          try {
            onEvent(JSON.parse(payload) as StreamEvent)
          } catch {
            /* 半个包，忽略 */
          }
        }
      }
    })()
  },

  // ---- 学期视图 ----
  getSemester: (day?: string) =>
    req<WeekView>('/semester' + (day ? `?day=${day}` : '')),
  getSemesterMeta: () => req<SemesterMeta>('/semester/meta'),
  putCourses: (courses: unknown[]) =>
    req<{ ok: boolean; count: number }>('/semester/courses', {
      method: 'PUT',
      ...jsonBody({ courses }),
    }),
  putAssignments: (assignments: unknown[]) =>
    req<{ ok: boolean; count: number }>('/semester/assignments', {
      method: 'PUT',
      ...jsonBody({ assignments }),
    }),
  resetSemester: () =>
    req<{ ok: boolean; message: string }>('/semester/reset', { method: 'POST' }),

  // ---- 原页图 ----
  pageUrl: (docId: string, pageNo: number, dpi = 110) =>
    `${BASE}/page/${encodeURIComponent(docId)}/${pageNo}?dpi=${dpi}`,
}
