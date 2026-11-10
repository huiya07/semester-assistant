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
  ChevronUp,
  Clock,
  Inbox,
  Loader2,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Send,
  Settings2,
  Square,
  Trash2,
  X,
} from 'lucide-react'
import { ApiError, api } from './api'
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

/**
 * PDF 抽出来的文本保留了原始硬换行，直接渲染会出现「1.」独占一行、
 * 「偏。」「，并说明原因。」这种标点悬在行首的观感。
 * 这里按空行分段，段内单换行合并成空格，让浏览器自然重排；段落结构仍然保留。
 */
function tidySnippet(t: string): string {
  return t
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
    .join('\n\n')
}

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
  const imgRef = useRef<HTMLImageElement>(null)

  // 展开原页后图片常落在折叠线以下，等它渲染出来再滚到可视区
  useEffect(() => {
    if (!showPage) return
    const t = setTimeout(
      () => imgRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }),
      120,
    )
    return () => clearTimeout(t)
  }, [showPage])

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
          transition={{
            height: { duration: open ? 0.28 : 0.16, ease: open ? [0.22, 1, 0.36, 1] : 'easeIn' },
            opacity: { duration: open ? 0.22 : 0.12 },
          }}
          className="overflow-hidden border-t border-surface-3 px-3 py-2.5"
        >
          <div className="mb-2 text-[12px] text-ink-400">命中片段</div>
          <p className="whitespace-pre-wrap break-words rounded-field bg-surface-1 px-3 py-2 text-[13px] leading-relaxed text-ink-700">
            {tidySnippet(c.text)}
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
              ref={imgRef}
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
  // 长回答折叠：流式过程中不折（内容还在长），结束后按实际高度决定
  const [expanded, setExpanded] = useState(false)
  const [overflows, setOverflows] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (m.status === 'streaming') return
    const el = bodyRef.current
    if (el) setOverflows(el.scrollHeight > 280)
  }, [m.text, m.status])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
      className="mb-8"
    >
      {/* 用户消息 */}
      <div className="mb-3 flex justify-end">
        <div className="max-w-[75%] break-words rounded-card rounded-br-sm bg-surface-2 px-4 py-2.5 text-[14px] leading-relaxed text-ink-900">
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

          {/* not_found 的正文改由下面的琥珀警示框承载，这里不再重复渲染一遍 */}
          {m.text && m.status !== 'not_found' && (
            <>
              <div
                ref={bodyRef}
                className={`md-body text-[14px] leading-[1.75] text-ink-900 ${
                  overflows && !expanded ? 'max-h-[280px] overflow-hidden' : ''
                }`}
                style={
                  overflows && !expanded
                    ? { maskImage: 'linear-gradient(to bottom, #000 72%, transparent)' }
                    : undefined
                }
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                {m.status === 'streaming' && <span className="sa-caret" />}
              </div>
              {overflows && (
                <button
                  onClick={() => setExpanded((v) => !v)}
                  className="mt-1 flex items-center gap-1 text-[12px] text-brand-600 transition-colors hover:text-brand-700"
                >
                  {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {expanded ? '收起' : '展开全文'}
                </button>
              )}
            </>
          )}

          {m.status === 'not_found' && (
            <div className="mt-2 flex items-start gap-2 rounded-field border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-800">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>{m.text}</span>
            </div>
          )}

          {m.status !== 'streaming' && m.searched.length > 0 && (
            <p className="mt-2 flex items-start gap-1.5 text-[12px] leading-relaxed text-ink-500">
              <Search size={12} className="mt-[3px] shrink-0" />
              <span>{m.searched.join('；')}</span>
            </p>
          )}

          {m.elapsed !== undefined && (
            <p className="mt-1 flex items-center gap-1.5 text-[12px] text-ink-500">
              <Clock size={12} className="shrink-0" />
              <span>用时 {m.elapsed < 0.1 ? '不到 0.1' : m.elapsed.toFixed(1)} 秒</span>
            </p>
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
  courseNames,
  uploadCourse,
  onCourseChange,
}: {
  docs: DocItem[]
  totalCunks: number
  onUpload: (f: File) => void
  onDelete: (d: DocItem) => void
  uploading: boolean
  courseNames: string[]
  uploadCourse: string
  onCourseChange: (c: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <aside className="flex h-full w-[268px] shrink-0 flex-col border-r border-surface-3 bg-surface-0">
      <div className="px-4 pb-3 pt-5">
        <h1 className="flex items-center gap-2 text-[16px] font-semibold text-ink-900">
          <BookOpen size={18} className="text-brand-600" />
          学期助手
        </h1>
        <p className="mt-1 text-[12px] leading-relaxed text-ink-500">
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
          data-guide="upload"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-2 rounded-field border border-dashed border-surface-3 bg-surface-1 py-2.5 text-[13px] text-ink-500 transition-colors hover:border-brand-300 hover:text-brand-600 disabled:opacity-60"
        >
          {uploading ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
          {uploading ? '正在解析并建立索引…' : '添加资料（PDF）'}
        </button>

        <label className="mt-2 flex items-center gap-1.5 text-[11px] text-ink-500">
          归属课程
          <select
            value={uploadCourse}
            onChange={(e) => onCourseChange(e.target.value)}
            className="min-w-0 flex-1 rounded-[6px] border border-surface-3 bg-surface-0 px-1.5 py-1 text-[11px] text-ink-700 outline-none transition-colors duration-150 focus:border-brand-400"
          >
            <option value="">未分类</option>
            {courseNames.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <div className="px-2 pb-1.5 text-[11px] uppercase tracking-wide text-ink-500">
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
            {d.course && (
              <span
                className="shrink-0 rounded bg-brand-50 px-1 py-0.5 text-[10px] text-brand-700"
                title={`归属课程：${d.course}`}
              >
                {d.course.length > 4 ? d.course.slice(0, 4) : d.course}
              </span>
            )}
            <span className="shrink-0 text-[11px] text-ink-500">{d.chunks}</span>
            <button
              onClick={() => onDelete(d)}
              className="shrink-0 rounded p-1.5 text-ink-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-brand-400"
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
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [clearOpen, setClearOpen] = useState(false)

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
      setMsg({ ok: true, text: r.message })
      setApiKey('')
      onSaved()
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
    <div className="border-b border-surface-3 bg-surface-0">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-2 px-5 py-2.5 text-left text-[13px] text-ink-500 hover:bg-surface-1"
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

      <AnimatePresence initial={false}>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden"
        >
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
              onClick={() => setClearOpen(true)}
              className="rounded-field border border-surface-3 px-4 py-1.5 text-[13px] text-ink-500 hover:bg-surface-1"
            >
              清除（回退 .env）
            </button>
            {msg && (
              <span
                className={`text-[12px] ${msg.ok ? 'text-brand-700' : 'text-red-600'}`}
                role="status"
              >
                {msg.text}
              </span>
            )}
          </div>
        </div>
        </motion.div>
      )}
      </AnimatePresence>
    </div>

    <ConfirmationDialog
      isOpen={clearOpen}
      onClose={() => setClearOpen(false)}
      onConfirm={async () => {
        setClearOpen(false)
        try {
          const r = await api.clearSettings()
          setMsg({ ok: true, text: r.message })
          onSaved()
        } catch (e) {
          setMsg({ ok: false, text: (e as Error).message })
        }
      }}
      title="清除模型配置"
      description="要清除界面里保存的 Base URL / API Key / 模型名吗？清除后会回退到项目根目录 .env 里的配置。"
      confirmLabel="确认清除"
      cancelLabel="取消"
      variant="danger"
      size="md"
    />
    </>
  )
}

// ---------------------------------------------------------------- 周视图

function WeekPanel({ view }: { view: WeekView | null }) {
  // 周视图每列只有约 140px，作业标题必然被截断；点击看完整内容
  const [detail, setDetail] = useState<{ course: string; title: string; due: string } | null>(null)

  if (!view) return <div className="p-8 text-[13px] text-ink-400">加载中…</div>
  if (view.before_semester)
    return <div className="p-8 text-[13px] text-ink-500">学期还没开始（开学日 {view.monday}）。</div>

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h2 className="text-[15px] font-semibold text-ink-900">
          第 {view.week_no} 周 · {view.monday} 起
        </h2>
        <span
          className={`rounded px-1.5 py-0.5 text-[11px] ${
            view.courses_custom
              ? 'bg-brand-50 text-brand-700'
              : 'bg-surface-2 text-ink-500'
          }`}
        >
          {view.courses_custom ? '自定义课表' : '示例数据'}
        </span>
        {!view.courses_custom && (
          <span className="text-[11px] text-ink-400">
            可在下方「导入 / 管理」换成你自己的课表与作业
          </span>
        )}
      </div>

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
              <span className="text-[11px] text-ink-500">{d.date.slice(5)}</span>
            </div>

            {d.courses.length === 0 && d.due.length === 0 && (
              <div className="py-2 text-center text-[11px] text-ink-500">—</div>
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
              <button
                key={a.id}
                type="button"
                onClick={() => setDetail({ course: a.course, title: a.title, due: a.due_date })}
                className="mb-1.5 block w-full rounded bg-red-50 px-1.5 py-1 text-left transition-colors hover:bg-red-100 focus-visible:ring-2 focus-visible:ring-red-400"
                title={`${a.course} · ${a.title}（点击查看完整内容）`}
              >
                <div className="truncate text-[11px] font-medium text-red-700">
                  ⚠ {a.course}
                </div>
                <div className="truncate text-[11px] text-red-700">
                  {a.title}
                </div>
              </button>
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

      {/* 作业详情：列宽只有 140px 左右，完整内容放这里看 */}
      {detail && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/25 backdrop-blur-[2px]"
          onClick={() => setDetail(null)}
        >
          <div
            className="w-[380px] rounded-card bg-surface-0 p-5 shadow-pop"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-start justify-between gap-3">
              <span className="rounded bg-red-50 px-1.5 py-0.5 text-[11px] text-red-700">作业</span>
              <button
                onClick={() => setDetail(null)}
                className="rounded p-1 text-ink-400 hover:bg-surface-1"
                aria-label="关闭"
              >
                <X size={14} />
              </button>
            </div>
            <div className="text-[15px] font-semibold text-ink-900">{detail.course}</div>
            <p className="mt-1.5 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-ink-700">
              {detail.title}
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[12px] text-ink-500">
              <Clock size={12} />
              截止 {detail.due}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- 首次访问引导

const GUIDE_KEY = 'sa_guide_seen_v1'

interface GuideStep {
  sel: string
  title: string
  desc: string
  place: 'right' | 'top' | 'bottom'
}

const GUIDE_STEPS: GuideStep[] = [
  {
    sel: '[data-guide="upload"]',
    title: '先添加一份课程资料',
    desc: '支持带文本层的 PDF。可以先从仓库自带的示例讲义试起，也可以选个归属课程，之后提问时能按课程筛选。',
    place: 'right',
  },
  {
    sel: '[data-guide="input"]',
    title: '在这里提问',
    desc: '每个答案都会标注页码，点开能对照原文；资料里没有的内容，它会直接说找不到，不会编。',
    place: 'top',
  },
  {
    sel: '[data-guide="week"]',
    title: '顺便看这周的安排',
    desc: '课表和到期作业都在这一页，红色的是今天要交的。点作业可以看完整标题。',
    place: 'bottom',
  },
]

function GuideRing({ rect }: { rect: DOMRect }) {
  return (
    <div
      className="pointer-events-none absolute rounded-field transition-all duration-300"
      style={{
        top: rect.top - 6,
        left: rect.left - 6,
        width: rect.width + 12,
        height: rect.height + 12,
        // 靛蓝描边 + 白色光晕：目标元素多是白的，纯白描边会糊在一起
        boxShadow:
          '0 0 0 2px #557dbf, 0 0 0 6px rgba(255,255,255,0.45), 0 10px 30px rgba(31,30,29,0.35)',
      }}
    />
  )
}

function GuideBubble({
  rect,
  step,
  index,
  total,
  onNext,
  onSkip,
}: {
  rect: DOMRect
  step: GuideStep
  index: number
  total: number
  onNext: () => void
  onSkip: () => void
}) {
  const W = 320
  const GAP = 18
  let style: React.CSSProperties = {}
  if (step.place === 'right') {
    style = { top: Math.max(12, Math.min(rect.top, window.innerHeight - 220)), left: rect.right + GAP, width: W }
  } else if (step.place === 'top') {
    const left = Math.max(12, Math.min(rect.left, window.innerWidth - W - 12))
    style = { bottom: window.innerHeight - rect.top + GAP, left, width: W }
  } else {
    const left = Math.max(12, Math.min(rect.left, window.innerWidth - W - 12))
    style = { top: rect.bottom + GAP, left, width: W }
  }

  return (
    <div
      className="absolute rounded-card bg-surface-0 p-4 shadow-pop"
      style={style}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[11px] text-ink-400">
          {index} / {total}
        </span>
        <button onClick={onSkip} className="text-[11px] text-ink-400 hover:text-ink-700">
          跳过引导
        </button>
      </div>
      <h3 className="text-[14px] font-semibold text-ink-900">{step.title}</h3>
      <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-600">{step.desc}</p>
      <button
        onClick={onNext}
        className="mt-3 w-full rounded-field bg-brand-600 py-1.5 text-[13px] text-white transition-colors hover:bg-brand-700"
      >
        {index === total ? '完成' : '下一步'}
      </button>
    </div>
  )
}

function FirstRunGuide({ onDone }: { onDone: () => void }) {
  const [index, setIndex] = useState(0)
  const [rect, setRect] = useState<DOMRect | null>(null)
  // 必须区分「还没算出来」和「真的找不到」：
  // 之前两者共用 rect=null，导致每次切换步骤的 220ms 间隙里兜底卡会闪一下
  const [status, setStatus] = useState<'locating' | 'ok' | 'missing'>('locating')

  useEffect(() => {
    setStatus('locating')
    // 等布局稳定（字体/图标加载会微调高度）
    const t = setTimeout(() => {
      const el = document.querySelector(GUIDE_STEPS[index].sel)
      if (el) {
        setRect(el.getBoundingClientRect())
        setStatus('ok')
      } else {
        setStatus('missing')
      }
    }, 220)
    return () => clearTimeout(t)
  }, [index])

  const step = GUIDE_STEPS[index]
  const isLast = index === GUIDE_STEPS.length - 1
  const next = () => (isLast ? onDone() : setIndex((i) => i + 1))

  return (
    <div className="fixed inset-0 z-[70]">
      <div className="absolute inset-0 bg-ink-900/55" onClick={next} />

      {rect && <GuideRing rect={rect} />}
      {status === 'locating' ? null : status === 'ok' && rect ? (
        <GuideBubble
          rect={rect}
          step={step}
          index={index + 1}
          total={GUIDE_STEPS.length}
          onNext={next}
          onSkip={onDone}
        />
      ) : (
        // 目标元素找不到时不能把用户卡在这里
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-card bg-surface-0 p-5 shadow-pop">
          <p className="mb-3 text-[13px] text-ink-700">引导暂时无法定位界面元素。</p>
          <button
            onClick={onDone}
            className="rounded-field bg-brand-600 px-4 py-1.5 text-[13px] text-white"
          >
            跳过引导
          </button>
        </div>
      )}

      {/* 任何时候都能退出的固定入口 */}
      <button
        onClick={onDone}
        className="absolute right-6 top-6 rounded-field border border-white/30 bg-ink-900/40 px-3 py-1.5 text-[12px] text-white backdrop-blur-sm transition-colors hover:bg-ink-900/60"
      >
        跳过引导
      </button>
    </div>
  )
}

// ---------------------------------------------------------------- 课表导入

function ImportPanel({ onChanged }: { onChanged: () => void }) {
  const [meta, setMeta] = useState<SemesterMeta | null>(null)
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
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
    <>
    <div className="mt-8 rounded-card border border-surface-3 bg-surface-0">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-[13px] text-ink-500 hover:bg-surface-1"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Inbox size={14} />
        导入 / 管理课表与作业
      </button>

      <AnimatePresence initial={false}>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden"
        >
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
                onClick={() => setResetOpen(true)}
              >
                恢复默认
              </CdsButton>
            )}
            {msg && <span className="text-[12px] text-ink-500">{msg}</span>}
          </div>

          <div className="space-y-1.5 rounded-field bg-surface-1 px-3 py-2.5">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <span className="shrink-0 rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-600">
                课表
              </span>
              <span className="text-[12px] text-ink-500">
                必填 <code className="text-ink-700">name</code> ·
                <code className="text-ink-700"> day</code>（1–7）·
                <code className="text-ink-700"> weeks</code>（数组），可选
                <code className="text-ink-700"> start_section / end_section / start_time / end_time</code>
              </span>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <span className="shrink-0 rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-600">
                作业
              </span>
              <span className="text-[12px] text-ink-500">
                必填 <code className="text-ink-700">id</code> ·
                <code className="text-ink-700"> course</code> ·
                <code className="text-ink-700"> title</code> ·
                <code className="text-ink-700"> due_date</code>（YYYY-MM-DD）
              </span>
            </div>
          </div>
        </div>
        </motion.div>
      )}
      </AnimatePresence>
    </div>

    <ConfirmationDialog
      isOpen={resetOpen}
      onClose={() => setResetOpen(false)}
      onConfirm={async () => {
        setResetOpen(false)
        try {
          const r = await api.resetSemester()
          setMsg(r.message)
          await refresh()
          onChanged()
        } catch (e) {
          setMsg(`恢复失败：${(e as Error).message}`)
        }
      }}
      title="恢复默认数据"
      description="要用仓库自带的示例数据替换当前课表与作业吗？已导入的自定义数据会被删除，且无法撤销。"
      confirmLabel="确认恢复"
      cancelLabel="取消"
      variant="danger"
      size="md"
    />
    </>
  )
}

// ---------------------------------------------------------------- 主应用

export default function App() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [totalChunks, setTotalChunks] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [settings, setSettings] = useState<SettingsPayload | null>(null)
  const [courseNames, setCourseNames] = useState<string[]>([])
  const [uploadCourse, setUploadCourse] = useState('')
  const [askCourse, setAskCourse] = useState('')

  const [tab, setTab] = useState<'ask' | 'week'>('ask')
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [week, setWeek] = useState<WeekView | null>(null)
  const [pendingDelete, setPendingDelete] = useState<DocItem | null>(null)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  const [guideOpen, setGuideOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const [inkBar, setInkBar] = useState({ left: 0, width: 0 })

  // 首次访问才弹引导；localStorage 不可用（隐私模式）时静默跳过
  useEffect(() => {
    try {
      if (!localStorage.getItem(GUIDE_KEY)) setGuideOpen(true)
    } catch {
      /* 忽略 */
    }
  }, [])

  // tab 下划线跟着当前页滑动，而不是瞬移
  useEffect(() => {
    const el = tabRefs.current[tab]
    if (el) setInkBar({ left: el.offsetLeft, width: el.offsetWidth })
  }, [tab, guideOpen])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4200)
    return () => clearTimeout(t)
  }, [toast])

  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const taRef = useRef<HTMLTextAreaElement>(null)

  // 输入框随内容增高（上限 160px），否则多行问题被压成一行滚动条
  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [question])

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
    api
      .getCourseNames()
      .then((r) => setCourseNames(r.names))
      .catch(() => {})
  }, [refreshLibrary, refreshSettings])

  useEffect(() => {
    // 流式过程中每来一段都跟到底部；用锚点而不是容器 ref，兼容 CDS 的滚动容器
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [msgs])

  const upload = async (f: File) => {
    setUploading(true)
    try {
      const r = await api.uploadPdf(f, uploadCourse)
      await refreshLibrary()
      const tag = uploadCourse ? ` · ${uploadCourse}` : ''
      setToast({ kind: 'ok', msg: `已入库 ${r.doc_name}：${r.pages} 页 · ${r.chunks} 个片段${tag}` })
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
        askCourse || undefined,
      )
    } catch (e) {
      const kind = e instanceof ApiError ? e.kind : 'network'
      if (kind !== 'aborted') {
        setMsgs((prev) =>
          prev.map((m) =>
            m.id === id ? { ...m, status: 'error', text: (e as Error).message } : m,
          ),
        )
      } else {
        // 用户主动停止：保留已经出来的内容，标记完成而不是报错
        setMsgs((prev) =>
          prev.map((m) =>
            m.id === id
              ? { ...m, status: m.text ? 'ok' : 'not_found', text: m.text || '已停止。' }
              : m,
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
      <AnimatePresence initial={false}>
      {sidebarOpen && (
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 268, opacity: 1 }}
        exit={{ width: 0, opacity: 0 }}
        transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
        className="shrink-0 overflow-hidden"
      >
      <Sidebar
        docs={docs}
        totalCunks={totalChunks}
        onUpload={upload}
        onDelete={setPendingDelete}
        uploading={uploading}
        courseNames={courseNames}
        uploadCourse={uploadCourse}
        onCourseChange={setUploadCourse}
      />
      </motion.div>
      )}
      </AnimatePresence>

      <main className="flex min-w-0 flex-1 flex-col">
        <SettingsPanel settings={settings} onSaved={refreshSettings} />

        {/* Tab 栏 */}
        <div className="relative flex shrink-0 items-center gap-1 border-b border-surface-3 bg-surface-0 px-4">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            title={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
            aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
            className="mr-1 rounded p-1.5 text-ink-400 transition-colors hover:bg-surface-1 hover:text-ink-700"
          >
            {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
          </button>
          <motion.div
            className="absolute bottom-0 h-[2px] rounded-full bg-brand-600"
            animate={{ left: inkBar.left, width: inkBar.width }}
            transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
            initial={false}
          />
          {(
            [
              ['ask', '资料问答', MessageSquare],
              ['week', '这周该做什么', CalendarDays],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              ref={(el) => {
                tabRefs.current[key] = el
              }}
              data-guide={key}
              onClick={() => setTab(key)}
              className={`relative flex items-center gap-1.5 px-3 py-2.5 text-[13px] transition-colors ${
                tab === key ? 'text-brand-700' : 'text-ink-400 hover:text-ink-700'
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={tab}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
          className={
            tab === 'ask'
              ? 'relative flex min-h-0 flex-1 flex-col'
              : 'flex-1 overflow-y-auto'
          }
        >
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
                                <div className="mt-0.5 text-[12px] leading-relaxed text-ink-500">
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
                              onClick={() => {
                                setQuestion(q)
                                requestAnimationFrame(() => taRef.current?.focus())
                              }}
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
                {/* scroll-mb 让锚点停在输入框上方，不被悬浮的玻璃条盖住 */}
                <div ref={endRef} className="h-px scroll-mb-[240px]" />
              </div>
            </ScrollFadeContainer>

            {/* 底部渐隐：让消息自然隐去，衬托悬浮输入框 */}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-surface-1 via-surface-1/85 to-transparent" />

            {/* 悬浮玻璃输入框 */}
            <div className="absolute inset-x-0 bottom-0 z-10 px-6 pb-5">
              <div className="mx-auto max-w-[760px]" data-guide="input">
              {courseNames.length > 0 && (
                <div className="mb-1.5 flex items-center gap-1.5 pl-1 text-[11px] text-ink-500">
                  <Search size={11} />
                  限定课程
                  <select
                    value={askCourse}
                    onChange={(e) => setAskCourse(e.target.value)}
                    className="rounded-[6px] border border-surface-3 bg-surface-0/80 px-1.5 py-0.5 text-[11px] text-ink-700 outline-none transition-colors duration-150 focus:border-brand-400"
                  >
                    <option value="">全部课程</option>
                    {courseNames.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                  <span className="text-ink-400">未分类的资料始终参与检索</span>
                </div>
              )}
              <div className="flex items-end gap-2 rounded-card border border-white/70 bg-white/70 p-1.5 shadow-[0_10px_36px_rgba(31,30,29,0.12)] backdrop-blur-xl transition-[box-shadow,border-color] duration-200 focus-within:border-brand-300 focus-within:shadow-[0_10px_36px_rgba(63,97,163,0.20)] focus-within:ring-2 focus-within:ring-brand-500/15">
                <textarea
                  ref={taRef}
                  value={question}
                  aria-label="输入问题"
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      send()
                    }
                  }}
                  rows={1}
                  placeholder="问点什么…（Enter 发送，Shift+Enter 换行）"
                  className="max-h-40 min-h-[38px] flex-1 resize-none rounded-field bg-transparent px-3 py-2 text-[14px] leading-relaxed text-ink-900 outline-none transition-colors placeholder:text-ink-400"
                />
                <button
                  onClick={() => (busy ? abortRef.current?.abort() : send())}
                  disabled={!busy && !question.trim()}
                  title={busy ? '停止生成' : '发送'}
                  aria-label={busy ? '停止生成' : '发送'}
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-field text-white transition-all active:scale-95 disabled:bg-surface-3 disabled:text-ink-300 ${
                    busy ? 'bg-ink-500 hover:bg-ink-700' : 'bg-brand-600 hover:bg-brand-700'
                  }`}
                >
                  {busy ? <Square size={13} fill="currentColor" /> : <Send size={15} />}
                </button>
              </div>
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
        </motion.div>
        </AnimatePresence>
      </main>

      {/* 轻提示 */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className={`pointer-events-none fixed bottom-24 right-6 z-[60] max-w-[380px] rounded-field border px-4 py-2.5 text-[13px] shadow-pop ${
              toast.kind === 'ok'
                ? 'border-brand-200 bg-brand-50 text-brand-800'
                : 'border-red-200 bg-red-50 text-red-700'
            }`}
          >
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 首次访问引导 */}
      {guideOpen && (
        <FirstRunGuide
          onDone={() => {
            try {
              localStorage.setItem(GUIDE_KEY, '1')
            } catch {
              /* 忽略 */
            }
            setGuideOpen(false)
          }}
        />
      )}

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
        size="md"
      />
    </div>
  )
}
