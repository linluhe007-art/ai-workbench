export interface ApiErrorPayload {
  success?: boolean
  error_code?: string
  message?: string
  request_id?: string
  details?: unknown
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  LLM_NOT_CONFIGURED: '尚未配置 DeepSeek API Key',
  LLM_AUTH_FAILED: 'DeepSeek API Key 无效',
  LLM_RATE_LIMITED: '模型调用频率受限，请稍后重试',
  LLM_TIMEOUT: '模型调用超时',
  LLM_PROVIDER_ERROR: '模型服务暂时不可用',
  SEARCH_PROVIDER_ERROR: '搜索服务暂时不可用',
  TASK_NOT_FOUND: '任务不存在',
  NOT_FOUND: '资源不存在',
  VALIDATION_ERROR: '请求参数无效',
  PERMISSION_DENIED: '权限不足',
  INTERNAL_ERROR: '服务器内部错误，请查看 request_id',
}

export function getApiErrorCode(error: unknown): string | null {
  if (!error || typeof error !== 'object') return null
  const candidate = error as { response?: { data?: ApiErrorPayload } }
  const code = candidate.response?.data?.error_code
  return typeof code === 'string' && code ? code : null
}

export function getApiRequestId(error: unknown): string | null {
  if (!error || typeof error !== 'object') return null
  const candidate = error as { response?: { data?: ApiErrorPayload } }
  const requestId = candidate.response?.data?.request_id
  return typeof requestId === 'string' && requestId ? requestId : null
}

export function getFriendlyErrorMessage(error: unknown, fallback = '处理命令失败'): string {
  const code = getApiErrorCode(error)
  if (code && FRIENDLY_MESSAGES[code]) return FRIENDLY_MESSAGES[code]
  const candidate = error as { response?: { data?: ApiErrorPayload } }
  const message = candidate.response?.data?.message
  if (typeof message === 'string' && message) return message
  return fallback
}
