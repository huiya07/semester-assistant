import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  AlertTriangle,
  BookOpen,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Settings2,
  Trash2,
  X,
} from 'lucide-react'
import { api } from './api'
import { CdsButton } from './components/cds/CdsButton'
import { ConfirmationDialog } from './components/cds/ConfirmationDialog'
import { ScrollFadeContainer } from './components/cds/ScrollFadeContainer'
import { QuietDotsWave } from './components/cds/StatusIndicators'
import type {
  AnswerStatus,
  Citation,
  DocItem,
  SemesterMeta,
  SettingsPayload,
  WeekView,
} from './types'

// ---------------------------------------------------------------- 类型

interface Msg {
  id: number
  q: string
  status: AnswerStatus | 'streaming'
  text: string
  citations: Citation[]
  related: Citation[]
  searched: string[]
  elapsed?: number
}

// ---------------------------------------------------------------- 小组件

function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-[13px] text-ink-500">
      <Loader2 size={14} className="animate-spin" />
      {label}
    </span>
  )
}

/** 引用卡片：默认收起，展开后看原文，可选看原页。 */
function CitationCard({
  c,
  label,
  defaultOpen = false,
}: {
  c: Citation
  label: string
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const [showPage, setShowPage] = useState(false)

  return (
    <div className="mt-2 overflow-hidden rounded-field border border-surface-3 bg-surface-0 transition-shadow hover:shadow-soft">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-ink-700 transition-colors hover:bg-surface-1"
      >
        <motion.span
          animate={{ rotate: open ? 0 : 0 }}
          className="flex"
        >
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </motion.span>
        <span className="truncate">
          {label} · 《{c.doc_name}》第 {c.page_no} 页
        </span>
      </button>

      <AnimatePresence initial={false}>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden border-t border-surface-3 px-3 py-2.5"
        >
          <div className="mb-2 text-[12px] text-ink-400">命中片段</div>
          <p className="whitespace-pre-wrap rounded-field bg-surface-1 px-3 py-2 text-[13px] leading-relaxed text-ink-700">
            {c.text}
          </p>
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={() => setShowPage((v) => !v)}
              className="text-[12px] text-brand-600 hover:underline"
            >
              {showPage ? '收起原页' : '查看原页'}
            </button>
            <span className="text-[12px] text-ink-300">
              {c.pdf_file ? '' : '该资料已从资料库删除，无法查看原页'}
            </span>
          </div>
          {showPage && c.pdf_file && (
            <img
              src={api.pageUrl(c.doc_id, c.page_no)}
              alt={`第 ${c.page_no} 页`}
              className="mt-2 w-full rounded-field border border-surface-3"
            />
          )}
        </motion.div>
      )}
      </AnimatePresence>
    </div>
  )
}

function Message({ m }: { m: Msg }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
      className="mb-8"
    >
      {/* 用户消息 */}
      <div className="mb-3 flex justify-end">
        <div className="max-w-[75%] rounded-card rounded-br-sm bg-surface-2 px-4 py-2.5 text-[14px] leading-relaxed text-ink-900">
          {m.q}
        </div>
      </div>

      {/* 助手消息 */}
      <div className="flex gap-3">
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
          <BookOpen size={14} />
        </div>
        <div className="min-w-0 flex-1">
          {m.status === 'streaming' && !m.text && (
            <QuietDotsWave label="检索资料中…" />
          )}

          {m.text && (
            <div className="md-body text-[14px] leading-[1.75] text-ink-900">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
              {m.status === 'streaming' && <span className="sa-caret" />}
            </div>
          )}

          {m.status === 'not_found' && (
            <div className="mt-2 flex items-start gap-2 rounded-field border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-800">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>{m.text}</span>
            </div>
          )}

          {m.status !== 'streaming' && m.searched.length > 0 && (
            <p className="mt-2 text-[12px] text-ink-300">🔍 {m.searched.join('；')}</p>
          )}

          {m.elapsed !== undefined && (
            <p className="mt-1 text-[12px] text-ink-300">⏱ 用时 {m.elapsed.toFixed(1)} 秒</p>
          )}

          {m.citations.map((c, i) => (
            <CitationCard key={`c${i}`} c={c} label={`出处 [${c.index}]`} />
          ))}
          {m.related.map((c, i) => (
            <CitationCard key={`r${i}`} c={c} label="最接近的内容" />
          ))}
        </div>
      </div>
    </motion.div>
  )
}

// ---------------------------------------------------------------- 侧边栏

function Sidebar({
  docs,
  totalCunks,
  onUpload,
  onDelete,
  uploading,
}: {
  docs: DocItem[]
  totalCunks: number
  onUpload: (f: File) => void
  onDelete: (d: DocItem) => void
  uploading: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <aside className="flex w-[268px] shrink-0 flex-col border-r border-surface-3 bg-surface-0">
      <div className="px-4 pb-3 pt-5">
        <h1 className="flex items-center gap-2 text-[16px] font-semibold text-ink-900">
          <BookOpen size={18} className="text-brand-600" />
          学期助手
        </h1>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-400">
          资料问答 · 每条结论都带页码出处
        </p>
      </div>

      <div className="px-4 pb-3">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onUpload(f)
            e.target.value = ''
          }}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-2 rounded-field border border-dashed border-surface-3 bg-surface-1 py-2.5 text-[13px] text-ink-500 transition-colors hover:border-brand-300 hover:text-brand-600 disabled:opacity-60"
        >
          {uploading ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
          {uploading ? '正在解析并建立索引…' : '添加资料（PDF）'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <div className="px-2 pb-1.5 text-[11px] uppercase tracking-wide text-ink-300">
          资料库 · {docs.length} 篇 / {totalCunks} 片段
        </div>
        {docs.length === 0 && (
          <p className="px-2 py-3 text-[12px] text-ink-400">还是空的，先传一份 PDF。</p>
        )}
        {docs.map((d) => (
          <div
            key={d.doc_id}
            className="group flex items-center gap-2 rounded-field px-2 py-1.5 hover:bg-surface-1"
          >
            <span className="min-w-0 flex-1 truncate text-[13px] text-ink-700" title={d.doc_name}>
              {d.doc_name}
            </span>
            <span className="shrink-0 text-[11px] text-ink-300">{d.chunks}</span>
            <button
              onClick={() => onDelete(d)}
              className="shrink-0 rounded p-1 text-ink-300 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
              title="删除"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  )
}

// ---------------------------------------------------------------- 设置面板

function SettingsPanel({
  settings,
  onSaved,
}: {
  settings: SettingsPayload | null
  onSaved: () => void
}) {
  const [open, setOpen] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (settings) {
      setBaseUrl(settings.base_url)
      setModel(settings.model)
    }
  }, [settings])

  // 没配 key 时自动展开
  useEffect(() => {
    if (settings && !settings.has_key) setOpen(true)
  }, [settings])

  const save = async () => {
    setBusy(true)
    try {
      const r = await api.putSettings({ base_url: baseUrl, api_key: apiKey, model })
      setMsg(r.message)
      setApiKey('')
      onSaved()
    } catch (e) {
      setMsg((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-b border-surface-3 bg-surface-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-5 py-2.5 text-left text-[13px] text-ink-500 hover:bg-surface-1"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Settings2 size={14} />
        模型配置
        {settings && !settings.has_key && (
          <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800">
            还没配置 Key
          </span>
        )}
      </button>

      {open && (
        <div className="grid grid-cols-3 gap-3 px-5 pb-4">
          <label className="text-[12px] text-ink-500">
            API Base URL
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="mt-1 w-full rounded-field border border-surface-3 bg-surface-1 px-2.5 py-1.5 text-[13px] text-ink-900 outline-none focus:border-brand-400"
            />
          </label>
          <label className="text-[12px] text-ink-500">
            API Key
            <input
              type="password"
              value={apiKey}
              placeholder={settings?.has_key ? '已配置，留空表示不改' : 'sk-...'}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-1 w-full rounded-field border border-surface-3 bg-surface-1 px-2.5 py-1.5 text-[13px] text-ink-900 outline-none focus:border-brand-400"
            />
          </label>
          <label className="text-[12px] text-ink-500">
            模型名
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1 w-full rounded-field border border-surface-3 bg-surface-1 px-2.5 py-1.5 text-[13px] text-ink-900 outline-none focus:border-brand-400"
            />
          </label>
          <div className="col-span-3 flex items-center gap-3">
            <button
              onClick={save}
              disabled={busy}
              className="rounded-field bg-brand-600 px-4 py-1.5 text-[13px] text-white transition-colors hover:bg-brand-700 disabled:opacity-60"
            >
              {busy ? '保存中…' : '保存'}
            </button>
            <button
              onClick={async () => {
                const r = await api.clearSettings()
                setMsg(r.message)
                onSaved()
              }}
              className="rounded-field border border-surface-3 px-4 py-1.5 text-[13px] text-ink-500 hover:bg-surface-1"
            >
              清除（回退 .env）
            </button>
            {msg && <span className="text-[12px] text-ink-400">{msg}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- 周视图

function WeekPanel({ view }: { view: WeekView | null }) {
  if (!view) return <div className="p-8 text-[13px] text-ink-400">加载中…</div>
  if (view.before_semester)
    return <div className="p-8 text-[13px] text-ink-500">学期还没开始（开学日 {view.monday}）。</div>

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-6">
      <h2 className="mb-4 text-[15px] font-semibold text-ink-900">
        第 {view.week_no} 周 · {view.monday} 起
      </h2>

      <div className="grid grid-cols-7 gap-2">
        {view.days.map((d) => (
          <div
            key={d.date}
            className={`rounded-card border p-2.5 ${
              d.is_today
                ? 'border-brand-300 bg-brand-50'
                : 'border-surface-3 bg-surface-0'
            }`}
          >
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[12px] font-medium text-ink-700">{d.weekday}</span>
              <span className="text-[11px] text-ink-300">{d.date.slice(5)}</span>
            </div>

            {d.courses.length === 0 && d.due.length === 0 && (
              <div className="py-2 text-center text-[11px] text-ink-300">—</div>
            )}

            {d.courses.map((c, i) => (
              <div key={i} className="mb-1.5">
                <div className="truncate text-[12px] text-ink-900" title={c.name}>
                  {c.name}
                </div>
                <div className="text-[11px] text-ink-400">{c.slot}</div>
              </div>
            ))}

            {d.due.map((a) => (
              <div key={a.id} className="mb-1.5 rounded bg-red-50 px-1.5 py-1">
                <div className="truncate text-[11px] font-medium text-red-700" title={a.course}>
                  ⚠ {a.course}
                </div>
                <div className="truncate text-[11px] text-red-600/80" title={a.title}>
                  {a.title}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-[13px] font-medium text-ink-700">接下来两周要交</h3>
        {view.upcoming.length === 0 ? (
          <p className="text-[12px] text-ink-400">接下来两周没有到期作业。</p>
        ) : (
          <ul className="space-y-1">
            {view.upcoming.map((a) => (
              <li key={a.id} className="text-[13px] text-ink-700">
                <code className="mr-2 rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-500">
                  {a.due_date}
                </code>
                <strong>{a.course}</strong> · {a.title}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- 课表导入

function ImportPanel({ onChanged }: { onChanged: () => void }) {
  const [meta, setMeta] = useState<SemesterMeta | null>(null)
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const cRef = useRef<HTMLInputElement>(null)
  const aRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(async () => {
    setMeta(await api.getSemesterMeta())
  }, [])

  useEffect(() => {
    refresh().catch(() => {})
  }, [refresh])

  const uploadOne = async (file: File, kind: 'courses' | 'assignments') => {
    setBusy(true)
    try {
      const text = await file.text()
      let data = JSON.parse(text)
      if (Array.isArray(data)) data = { [kind]: data }
      const list = data?.[kind]
      if (!Array.isArray(list)) throw new Error(`${file.name} 缺少 ${kind} 数组`)
      const r =
        kind === 'courses' ? await api.putCourses(list) : await api.putAssignments(list)
      setMsg(`已导入 ${file.name}：${r.count} 条`)
      await refresh()
      onChanged()
    } catch (e) {
      setMsg(`导入失败：${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-8 rounded-card border border-surface-3 bg-surface-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-[13px] text-ink-500 hover:bg-surface-1"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        📥 导入 / 管理课表与作业
      </button>

      {open && (
        <div className="space-y-3 border-t border-surface-3 px-4 py-3">
          <p className="text-[12px] text-ink-500">
            当前课表：<strong>{meta?.courses ?? '—'}</strong> 条（
            {meta?.custom_courses ? '自定义' : '示例'}）　·　当前作业：
            <strong>{meta?.assignments ?? '—'}</strong> 条（
            {meta?.custom_assignments ? '自定义' : '示例'}）
          </p>

          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={cRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadOne(f, 'courses')
                e.target.value = ''
              }}
            />
            <input
              ref={aRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadOne(f, 'assignments')
                e.target.value = ''
              }}
            />
            <CdsButton variant="outline" size="sm" onClick={() => cRef.current?.click()} disabled={busy}>
              导入课表 JSON
            </CdsButton>
            <CdsButton variant="outline" size="sm" onClick={() => aRef.current?.click()} disabled={busy}>
              导入作业 JSON
            </CdsButton>
            {(meta?.custom_courses || meta?.custom_assignments) && (
              <CdsButton
                variant="danger"
                size="sm"
                onClick={async () => {
                  if (!confirm('要用示例数据替换当前课表与作业吗？已导入的自定义数据会被删除，且无法撤销。')) return
                  const r = await api.resetSemester()
                  setMsg(r.message)
                  await refresh()
                  onChanged()
                }}
              >
                恢复默认
              </CdsButton>
            )}
            {msg && <span className="text-[12px] text-ink-400">{msg}</span>}
          </div>

          <p className="text-[11px] leading-relaxed text-ink-300">
            课表格式：<code className="rounded bg-surface-2 px-1">{'{ "courses": [ {"name","day","start_section","end_section","weeks"} ] }'}</code>
            <br />
            作业格式：<code className="rounded bg-surface-2 px-1">{'{ "assignments": [ {"id","course","title","due_date"} ] }'}</code>
          </p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- 主应用

export default function App() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [totalChunks, setTotalChunks] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [settings, setSettings] = useState<SettingsPayload | null>(null)

  const [tab, setTab] = useState<'ask' | 'week'>('ask')
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [week, setWeek] = useState<WeekView | null>(null)
  const [pendingDelete, setPendingDelete] = useState<DocItem | null>(null)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4200)
    return () => clearTimeout(t)
  }, [toast])

  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const refreshLibrary = useCallback(async () => {
    const r = await api.getLibrary()
    setDocs(r.docs)
    setTotalChunks(r.total_chunks)
  }, [])

  const refreshSettings = useCallback(async () => {
    setSettings(await api.getSettings())
  }, [])

  const refreshWeek = useCallback(async () => {
    setWeek(await api.getSemester())
  }, [])

  useEffect(() => {
    refreshLibrary().catch(() => {})
    refreshSettings().catch(() => {})
    api.getSemester().then(setWeek).catch(() => {})
  }, [refreshLibrary, refreshSettings])

  useEffect(() => {
    // 流式过程中每来一段都跟到底部；用锚点而不是容器 ref，兼容 CDS 的滚动容器
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [msgs])

  const upload = async (f: File) => {
    setUploading(true)
    try {
      const r = await api.uploadPdf(f)
      await refreshLibrary()
      setToast({ kind: 'ok', msg: `已入库 ${r.doc_name}：${r.pages} 页 · ${r.chunks} 个片段` })
    } catch (e) {
      setToast({ kind: 'err', msg: (e as Error).message })
    } finally {
      setUploading(false)
    }
  }

  const removeDoc = async (d: DocItem) => {
    try {
      await api.deleteDoc(d.doc_id)
      await refreshLibrary()
      setToast({ kind: 'ok', msg: `已删除《${d.doc_name}》` })
    } catch (e) {
      setToast({ kind: 'err', msg: (e as Error).message })
    } finally {
      setPendingDelete(null)
    }
  }

  const send = async () => {
    const q = question.trim()
    if (!q || busy) return
    setQuestion('')
    setBusy(true)

    const id = Date.now()
    setMsgs((prev) => [
      ...prev,
      { id, q, status: 'streaming', text: '', citations: [], related: [], searched: [] },
    ])

    const started = performance.now()
    const ac = new AbortController()
    abortRef.current = ac

    try {
      await api.askStream(
        q,
        (ev) => {
          setMsgs((prev) =>
            prev.map((m) => {
              if (m.id !== id) return m
              switch (ev.type) {
                case 'meta':
                  return { ...m, searched: ev.searched }
                case 'token':
                  return { ...m, text: m.text + ev.text }
                case 'done':
                  return {
                    ...m,
                    status: 'ok',
                    citations: ev.citations,
                    searched: ev.searched,
                    elapsed: (performance.now() - started) / 1000,
                  }
                case 'not_found':
                  return {
                    ...m,
                    status: 'not_found',
                    text: m.text || ev.text,
                    related: ev.related ?? [],
                    searched: ev.searched,
                    elapsed: (performance.now() - started) / 1000,
                  }
                case 'error':
                  return { ...m, status: 'error', text: ev.text }
                default:
                  return m
              }
            }),
          )
        },
        ac.signal,
      )
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setMsgs((prev) =>
          prev.map((m) =>
            m.id === id ? { ...m, status: 'error', text: (e as Error).message } : m,
          ),
        )
      }
    } finally {
      setBusy(false)
      abortRef.current = null
      setMsgs((prev) =>
        prev.map((m) => (m.id === id && m.status === 'streaming' ? { ...m, status: 'ok' } : m)),
      )
    }
  }

  return (
    <div className="flex h-full">
      <Sidebar
        docs={docs}
        totalCunks={totalChunks}
        onUpload={upload}
        onDelete={setPendingDelete}
        uploading={uploading}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <SettingsPanel settings={settings} onSaved={refreshSettings} />

        {/* Tab 栏 */}
        <div className="flex shrink-0 items-center gap-1 border-b border-surface-3 bg-surface-0 px-4">
          {(
            [
              ['ask', '资料问答', MessageSquare],
              ['week', '这周该做什么', CalendarDays],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-[13px] transition-colors ${
                tab === key
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-ink-400 hover:text-ink-700'
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {tab === 'ask' && (
          <div className="relative flex min-h-0 flex-1 flex-col">
            <ScrollFadeContainer orientation="vertical" fadeSize={30} className="flex-1">
              <div className="mx-auto max-w-[760px] px-6 pb-44 pt-6">
                {msgs.length === 0 && (
                  <div className="mx-auto max-w-[560px] py-12">
                    <BookOpen size={28} className="mx-auto mb-4 text-surface-3" />

                    {docs.length === 0 ? (
                      <>
                        <h2 className="mb-5 text-center text-[15px] font-semibold text-ink-900">
                          三步就能用起来
                        </h2>
                        <ol className="space-y-3.5">
                          {[
                            ['加一份资料', '左侧「添加资料」上传 PDF，自动解析并建立索引'],
                            ['提问', '问资料里的内容，每个回答都会标出 [1] 这样的出处'],
                            ['核对', '点开出处能看到命中原文，还可以展开 PDF 原页对照'],
                          ].map(([t, d], i) => (
                            <li key={t} className="flex gap-3">
                              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[11px] font-medium text-brand-700">
                                {i + 1}
                              </span>
                              <div>
                                <div className="text-[13px] font-medium text-ink-900">{t}</div>
                                <div className="mt-0.5 text-[12px] leading-relaxed text-ink-400">
                                  {d}
                                </div>
                              </div>
                            </li>
                          ))}
                        </ol>
                        <p className="mt-6 rounded-field border border-surface-3 bg-surface-2 px-3.5 py-2.5 text-[12px] leading-relaxed text-ink-500">
                          资料里没有的内容，它会直接说找不到，并把最接近的原文摆出来——不会编。
                        </p>
                      </>
                    ) : (
                      <div className="text-center">
                        <h2 className="mb-3 text-[15px] font-semibold text-ink-900">试试问：</h2>
                        <div className="inline-flex flex-col items-start gap-2">
                          {[
                            '这份资料讲了什么？',
                            `《${docs[0].doc_name}》的第 1 页说了什么？`,
                            '这份资料里没有的内容（看它会不会老实说找不到）',
                          ].map((q) => (
                            <button
                              key={q}
                              onClick={() => setQuestion(q)}
                              className="rounded-field border border-surface-3 bg-surface-0 px-3 py-1.5 text-left text-[13px] text-ink-600 transition-colors hover:border-brand-300 hover:text-brand-700"
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {msgs.map((m) => (
                  <Message key={m.id} m={m} />
                ))}
                <div ref={endRef} />
              </div>
            </ScrollFadeContainer>

            {/* 底部渐隐：让消息自然隐去，衬托悬浮输入框 */}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-surface-1 via-surface-1/85 to-transparent" />

            {/* 悬浮玻璃输入框 */}
            <div className="absolute inset-x-0 bottom-0 z-10 px-6 pb-5">
              <div className="mx-auto flex max-w-[760px] items-end gap-2 rounded-card border border-white/70 bg-white/70 p-1.5 shadow-[0_10px_36px_rgba(31,30,29,0.12)] backdrop-blur-xl">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      send()
                    }
                  }}
                  rows={1}
                  placeholder="问点什么…（Enter 发送，Shift+Enter 换行）"
                  className="max-h-40 min-h-[38px] flex-1 resize-none rounded-field bg-transparent px-3 py-2 text-[14px] leading-relaxed text-ink-900 outline-none transition-colors placeholder:text-ink-300"
                />
                <button
                  onClick={send}
                  disabled={busy || !question.trim()}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-field bg-brand-600 text-white transition-all hover:bg-brand-700 active:scale-95 disabled:bg-surface-3 disabled:text-ink-300"
                >
                  {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                </button>
              </div>
            </div>
          </div>
        )}

        {tab === 'week' && (
          <div className="flex-1 overflow-y-auto">
            <WeekPanel view={week} />
            <div className="mx-auto max-w-[1100px] px-6 pb-10">
              <ImportPanel onChanged={refreshWeek} />
            </div>
          </div>
        )}
      </main>

      {/* 轻提示 */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className={`fixed bottom-6 right-6 z-[60] max-w-[380px] rounded-field border px-4 py-2.5 text-[13px] shadow-pop ${
              toast.kind === 'ok'
                ? 'border-brand-200 bg-brand-50 text-brand-800'
                : 'border-red-200 bg-red-50 text-red-700'
            }`}
          >
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 删除确认（CDS ConfirmationDialog） */}
      <ConfirmationDialog
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && removeDoc(pendingDelete)}
        title="确认删除"
        description={
          pendingDelete
            ? `要删除《${pendingDelete.doc_name}》吗？将删除 ${pendingDelete.chunks} 个检索片段与留底的原件。此操作无法撤销。`
            : ''
        }
        confirmLabel="确认删除"
        cancelLabel="取消"
        variant="danger"
        size="sm"
      />
    </div>
  )
}
