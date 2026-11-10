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

/** 普通请求超时；上传/入库另给更长的预算（要解析 PDF + 建索引）。 */
const TIMEOUT_DEFAULT = 30_000
const TIMEOUT_UPLOAD = 180_000
/** 流式：等第一个字的上限，以及整体上限。 */
const TIMEOUT_FIRST_TOKEN = 25_000
const TIMEOUT_STREAM_TOTAL = 180_000

export type ErrKind = 'network' | 'timeout' | 'http' | 'aborted' | 'busy' | 'parse'

/** 带分类的错误：界面据此给不同措辞，而不是把 "Failed to fetch" 直接甩给用户。 */
export class ApiError extends Error {
  kind: ErrKind
  status?: number
  constructor(message: string, kind: ErrKind, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e
  const err = e as Error
  if (err?.name === 'AbortError' || err?.name === 'TimeoutError') {
    return new ApiError('请求超时了。检查一下网络，或者稍后再试。', 'timeout')
  }
  if (err?.name === 'TypeError') {
    // fetch 在断网 / DNS 失败 / CORS 时抛 TypeError，信息是英文的 Failed to fetch
    return new ApiError('连不上服务。确认后端还在运行，并检查网络连接。', 'network')
  }
  return new ApiError(err?.message || '发生了未知错误。', 'network')
}

async function req<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = TIMEOUT_DEFAULT,
): Promise<T> {
  const ac = new AbortController()
  const timer = setTimeout(() => ac.abort(new DOMException('timeout', 'TimeoutError')), timeoutMs)
  try {
    const res = await fetch(BASE + path, { ...init, signal: ac.signal })
    if (!res.ok) {
      let detail = `服务端返回 ${res.status}`
      try {
        const body = await res.json()
        detail = body.detail || detail
      } catch {
        /* 非 JSON 错误体，保持状态码 */
      }
      if (res.status === 429) {
        throw new ApiError(detail || '上一个请求还在处理中，稍等一下。', 'busy', 429)
      }
      throw new ApiError(detail, 'http', res.status)
    }
    return (await res.json()) as T
  } catch (e) {
    throw toApiError(e)
  } finally {
    clearTimeout(timer)
  }
}

/** 只对幂等的 GET 重试——入库、删除这类写操作绝不自动重放。 */
async function reqWithRetry<T>(path: string, retries = 2, timeoutMs = TIMEOUT_DEFAULT): Promise<T> {
  let last: ApiError | null = null
  for (let i = 0; i <= retries; i++) {
    try {
      return await req<T>(path, undefined, timeoutMs)
    } catch (e) {
      const err = toApiError(e)
      last = err
      // 只有网络/超时/5xx 值得再试；4xx 是请求本身的问题，重试没意义
      const retryable = err.kind === 'network' || err.kind === 'timeout' || (err.status ?? 0) >= 500
      if (!retryable || i === retries) break
      await new Promise((r) => setTimeout(r, 500 * (i + 1)))
    }
  }
  throw last ?? new ApiError('请求失败。', 'network')
}

function jsonBody(data: unknown): RequestInit {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

export const api = {
  // ---- 设置 ----
  getSettings: () => reqWithRetry<SettingsPayload>('/settings'),
  putSettings: (data: { base_url: string; api_key: string; model: string }) =>
    req<{ ok: boolean; message: string }>('/settings', { method: 'PUT', ...jsonBody(data) }),
  clearSettings: () =>
    req<{ ok: boolean; message: string }>('/settings/clear', { method: 'POST' }),

  // ---- 资料库 ----
  getLibrary: () => reqWithRetry<LibraryPayload>('/library'),
  deleteDoc: (docId: string) =>
    req<{ ok: boolean }>(`/library/${encodeURIComponent(docId)}`, { method: 'DELETE' }),
  uploadPdf: async (file: File, course = '') => {
    const fd = new FormData()
    fd.append('file', file)
    if (course) fd.append('course', course)
    return req<{ doc_id: string; doc_name: string; pages: number; chunks: number }>(
      '/library/upload',
      { method: 'POST', body: fd },
      TIMEOUT_UPLOAD,
    )
  },

  // ---- 问答 ----
  ask: (question: string, course?: string) =>
    req<AnswerPayload>('/ask', { method: 'POST', ...jsonBody({ question, course: course || null }) }),

  getCourseNames: () => reqWithRetry<{ names: string[] }>('/course-names'),

  /**
   * 流式问答。
   * 三道保险：首字超时（25s 内一个字都没有就放弃）、整体超时（180s）、外部主动中断。
   * 外部中断会以 kind='aborted' 抛出，界面不应把它当成错误展示。
   */
  askStream(
    question: string,
    onEvent: (ev: StreamEvent) => void,
    signal?: AbortSignal,
    course?: string,
    history?: { q: string; a: string }[],
  ): Promise<void> {
    return (async () => {
      const ac = new AbortController()
      const forwardAbort = () => ac.abort(new DOMException('aborted', 'AbortError'))
      signal?.addEventListener('abort', forwardAbort, { once: true })

      let gotFirst = false
      const firstTimer = setTimeout(
        () => ac.abort(new DOMException('timeout', 'TimeoutError')),
        TIMEOUT_FIRST_TOKEN,
      )
      const totalTimer = setTimeout(
        () => ac.abort(new DOMException('timeout', 'TimeoutError')),
        TIMEOUT_STREAM_TOTAL,
      )

      try {
        const res = await fetch(BASE + '/ask/stream', {
          method: 'POST',
          ...jsonBody({ question, course: course || null, history }),
          signal: ac.signal,
        })
        if (!res.ok || !res.body) {
          throw new ApiError(
            res.status === 429 ? '上一个问题还在回答中，稍等一下。' : `服务端返回 ${res.status}`,
            res.status === 429 ? 'busy' : 'http',
            res.status,
          )
        }

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
            let ev: StreamEvent
            try {
              ev = JSON.parse(payload) as StreamEvent
            } catch {
              continue // 半个包，丢掉
            }
            if (!gotFirst) {
              gotFirst = true
              clearTimeout(firstTimer) // 已经出字了，首个 token 超时不再生效
            }
            onEvent(ev)
          }
        }
      } catch (e) {
        if (signal?.aborted) throw new ApiError('已停止。', 'aborted')
        if (e instanceof ApiError) throw e
        const err = toApiError(e)
        // 首字超时和总超时要给不同的话
        if (err.kind === 'timeout' && !gotFirst) {
          throw new ApiError('等了 25 秒还没开始回答。检查网络，或换个更具体的问题。', 'timeout')
        }
        throw err
      } finally {
        clearTimeout(firstTimer)
        clearTimeout(totalTimer)
        signal?.removeEventListener('abort', forwardAbort)
      }
    })()
  },

  // ---- 学期视图 ----
  getSemester: (day?: string) =>
    reqWithRetry<WeekView>('/semester' + (day ? `?day=${day}` : '')),
  getSemesterMeta: () => reqWithRetry<SemesterMeta>('/semester/meta'),
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
