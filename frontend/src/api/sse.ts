/**
 * SSE 客户端：把 `fetch` 的流拆成事件，再交给调用方处理。
 *
 * 为什么不用 EventSource：EventSource 只能发 GET、不能带请求头（身份走三个 header），
 * 所以用 `fetch` + `ReadableStream` 自己按空行拆帧。
 */

export interface StreamEvent {
  event: string
  data: any
}

export interface StreamOptions {
  /** 外部中止（点"停止"按钮时用） */
  signal?: AbortSignal
  /** 每收到一个事件调一次；事件种类见后端 streaming.py 的协议表 */
  onEvent: (evt: StreamEvent) => void
}

function parseFrame(frame: string): StreamEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  const raw = dataLines.join('\n')
  try {
    return { event, data: JSON.parse(raw) }
  } catch {
    return { event, data: raw }
  }
}

async function readStream(resp: Response, options: StreamOptions): Promise<void> {
  if (!resp.body) throw new Error(`响应没有 body（HTTP ${resp.status}）`)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      const evt = parseFrame(frame)
      if (evt) options.onEvent(evt)
    }
  }
  const tail = parseFrame(buffer)
  if (tail) options.onEvent(tail)
}

/** 后端抛 HTTPException 时 body 是 `{"detail": "..."}`，直接拼原串会把 JSON 甩给用户看。 */
async function describeFailure(resp: Response): Promise<string> {
  const text = await resp.text()
  try {
    const parsed = JSON.parse(text) as { detail?: unknown }
    if (typeof parsed?.detail === 'string') return `HTTP ${resp.status}：${parsed.detail}`
  } catch {
    /* 不是 JSON 就按纯文本处理 */
  }
  return `HTTP ${resp.status}：${text || resp.statusText}`
}

/** 发一个 POST 并持续读 SSE（`/chat/stream` 与 `/resume` 共用）。 */
async function postStream(
  path: string,
  body: unknown,
  headers: Record<string, string>,
  options: StreamOptions,
): Promise<void> {
  const resp = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
    signal: options.signal,
  })
  if (!resp.ok) {
    throw new Error(await describeFailure(resp))
  }
  await readStream(resp, options)
}

export async function chatStream(
  message: string,
  threadId: string,
  headers: Record<string, string>,
  options: StreamOptions,
): Promise<void> {
  await postStream('/chat/stream', { message, thread_id: threadId }, headers, options)
}

export async function resumeStream(
  threadId: string,
  payload: unknown,
  headers: Record<string, string>,
  options: StreamOptions,
): Promise<void> {
  await postStream(`/runs/${encodeURIComponent(threadId)}/resume`, payload, headers, options)
}
