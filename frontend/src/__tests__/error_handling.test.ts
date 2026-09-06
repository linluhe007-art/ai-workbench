import { describe, it, expect } from 'vitest'
import {
  getApiErrorCode,
  getApiRequestId,
  getFriendlyErrorMessage,
} from '../utils/apiError'

function axiosError(data: unknown) {
  return { response: { data } }
}

describe('getApiErrorCode', () => {
  it('returns error_code from unified response', () => {
    expect(getApiErrorCode(axiosError({ error_code: 'LLM_NOT_CONFIGURED' }))).toBe('LLM_NOT_CONFIGURED')
  })

  it('returns null when error_code is missing', () => {
    expect(getApiErrorCode(axiosError({ message: 'x' }))).toBeNull()
  })

  it('returns null when response data is missing', () => {
    expect(getApiErrorCode(new Error('plain'))).toBeNull()
  })

  it('returns null for null input', () => {
    expect(getApiErrorCode(null)).toBeNull()
  })

  it('returns null when error_code is empty string', () => {
    expect(getApiErrorCode(axiosError({ error_code: '' }))).toBeNull()
  })
})

describe('getApiRequestId', () => {
  it('returns request_id from unified response', () => {
    expect(getApiRequestId(axiosError({ request_id: 'req-123' }))).toBe('req-123')
  })

  it('returns null when request_id is missing', () => {
    expect(getApiRequestId(axiosError({ message: 'x' }))).toBeNull()
  })

  it('returns null for non-object error', () => {
    expect(getApiRequestId('error')).toBeNull()
  })
})

describe('getFriendlyErrorMessage', () => {
  it('maps LLM_NOT_CONFIGURED to Chinese message', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'LLM_NOT_CONFIGURED' }))).toBe('尚未配置 DeepSeek API Key')
  })

  it('maps LLM_AUTH_FAILED', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'LLM_AUTH_FAILED' }))).toBe('DeepSeek API Key 无效')
  })

  it('maps LLM_RATE_LIMITED', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'LLM_RATE_LIMITED' }))).toBe('模型调用频率受限，请稍后重试')
  })

  it('maps LLM_TIMEOUT', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'LLM_TIMEOUT' }))).toBe('模型调用超时')
  })

  it('maps LLM_PROVIDER_ERROR', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'LLM_PROVIDER_ERROR' }))).toBe('模型服务暂时不可用')
  })

  it('maps SEARCH_PROVIDER_ERROR', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'SEARCH_PROVIDER_ERROR' }))).toBe('搜索服务暂时不可用')
  })

  it('maps TASK_NOT_FOUND', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'TASK_NOT_FOUND' }))).toBe('任务不存在')
  })

  it('maps NOT_FOUND', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'NOT_FOUND' }))).toBe('资源不存在')
  })

  it('maps VALIDATION_ERROR', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'VALIDATION_ERROR' }))).toBe('请求参数无效')
  })

  it('maps PERMISSION_DENIED', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'PERMISSION_DENIED' }))).toBe('权限不足')
  })

  it('maps INTERNAL_ERROR', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'INTERNAL_ERROR' }))).toBe('服务器内部错误，请查看 request_id')
  })

  it('uses server message when error_code is unknown', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'UNKNOWN', message: 'server said no' }))).toBe('server said no')
  })

  it('uses fallback when no code or message is present', () => {
    expect(getFriendlyErrorMessage(new Error('plain'))).toBe('处理命令失败')
  })

  it('uses custom fallback', () => {
    expect(getFriendlyErrorMessage(new Error('plain'), '自定义失败')).toBe('自定义失败')
  })

  it('returns fallback for empty error', () => {
    expect(getFriendlyErrorMessage(undefined)).toBe('处理命令失败')
  })

  it('prefers known code over server message', () => {
    expect(getFriendlyErrorMessage(axiosError({ error_code: 'TASK_NOT_FOUND', message: 'raw' }))).toBe('任务不存在')
  })

  it('handles string server message', () => {
    expect(getFriendlyErrorMessage(axiosError({ message: 'strange' }))).toBe('strange')
  })
})
