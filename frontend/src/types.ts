/** 与后端 backend/app/api.py 的返回结构一一对应。改这里必须同步改那边。 */

export interface Citation {
  index: number
  doc_id: string
  doc_name: string
  page_no: number
  text: string
  pdf_file: string
}

export type AnswerStatus = 'ok' | 'not_found' | 'error'

export interface AnswerPayload {
  status: AnswerStatus
  text: string
  citations: Citation[]
  related: Citation[]
  searched: string[]
  best_distance: number | null
  elapsed?: number
}

export interface DocItem {
  doc_id: string
  doc_name: string
  chunks: number
}

export interface LibraryPayload {
  docs: DocItem[]
  total_chunks: number
}

export interface CourseEntry {
  name: string
  slot: string
  start_section: number | null
  end_section: number | null
  start_time: string | null
  end_time: string | null
}

export interface AssignEntry {
  id: string
  course: string
  title: string
  due_date: string
}

export interface DayView {
  date: string
  weekday: string
  is_today: boolean
  courses: CourseEntry[]
  due: AssignEntry[]
}

export interface WeekView {
  week_no: number
  monday: string
  days: DayView[]
  course_count: number
  upcoming: AssignEntry[]
  before_semester: boolean
}

export interface SettingsPayload {
  base_url: string
  model: string
  has_key: boolean
}

export interface SemesterMeta {
  courses: number
  assignments: number
  custom_courses: boolean
  custom_assignments: boolean
}

/** 流式事件的联合类型，对应 qa.answer_stream() 的 yield。 */
export type StreamEvent =
  | { type: 'meta'; searched: string[]; best_distance: number | null }
  | { type: 'token'; text: string }
  | { type: 'done'; citations: Citation[]; searched: string[]; best_distance: number | null }
  | { type: 'not_found'; text: string; related?: Citation[]; searched: string[]; best_distance?: number }
  | { type: 'error'; text: string; detail?: string }
