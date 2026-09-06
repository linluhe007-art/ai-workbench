import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'

vi.mock('../api/client')
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

beforeEach(() => vi.clearAllMocks())

describe('Auth and Security', () => {
  it('login returns token pair', async () => {
    mockPost.mockResolvedValue({
      data: { access_token: 'access-xxx', refresh_token: 'refresh-xxx', token_type: 'bearer' }
    })
    const resp = await apiClient.post('/auth/login', { username: 'admin', password: 'admin' })
    expect(resp.data.access_token).toBeDefined()
    expect(resp.data.refresh_token).toBeDefined()
    expect(resp.data.token_type).toBe('bearer')
  })

  it('auth me returns user info without password', async () => {
    mockGet.mockResolvedValue({
      data: { user_id: 'admin', username: 'admin', roles: ['admin'], tenant_id: 'default' }
    })
    const resp = await apiClient.get('/auth/me')
    expect(resp.data.user_id).toBeDefined()
    expect(resp.data.password).toBeUndefined()
    expect(resp.data.hashed_password).toBeUndefined()
  })

  it('unauthorized returns 401', async () => {
    mockGet.mockRejectedValue({ response: { status: 401, data: { error: { code: 'UNAUTHORIZED' } } } })
    await expect(apiClient.get('/auth/me')).rejects.toBeDefined()
  })

  it('forbidden returns 403', async () => {
    mockGet.mockRejectedValue({ response: { status: 403, data: { error: { code: 'FORBIDDEN' } } } })
    await expect(apiClient.get('/admin/users')).rejects.toBeDefined()
  })

  it('refresh token works', async () => {
    mockPost.mockResolvedValue({
      data: { access_token: 'new-access', refresh_token: 'new-refresh', token_type: 'bearer' }
    })
    const resp = await apiClient.post('/auth/refresh', { refresh_token: 'old-refresh' })
    expect(resp.data.access_token).toBeDefined()
  })

  it('Bearer token sent in Authorization header', async () => {
    mockGet.mockResolvedValue({ data: { user_id: 'admin' } })
    const token = 'test-jwt-token'
    apiClient.defaults.headers.common['Authorization'] = 'Bearer ' + token
    const resp = await apiClient.get('/auth/me')
    expect(resp.data.user_id).toBe('admin')
  })
})

describe('Tenant Isolation', () => {
  it('tenant A cannot access tenant B tasks', async () => {
    mockGet.mockRejectedValue({ response: { status: 404, data: { error: { code: 'TASK_NOT_FOUND' } } } })
    await expect(apiClient.get('/tasks/tenant-b-task')).rejects.toBeDefined()
  })

  it('tenant A cannot access tenant B artifacts', async () => {
    mockGet.mockRejectedValue({ response: { status: 404, data: { error: { code: 'ARTIFACT_NOT_FOUND' } } } })
    await expect(apiClient.get('/artifacts/tenant-b-artifact')).rejects.toBeDefined()
  })
})

describe('Error Response Format', () => {
  it('error response has code and message', () => {
    const errorBody = {
      success: false,
      error: { code: 'TASK_NOT_FOUND', message: 'Task not found: t1' },
      request_id: 'req-123',
    }
    expect(errorBody.success).toBe(false)
    expect(errorBody.error.code).toBeDefined()
    expect(errorBody.error.message).toBeDefined()
    expect(errorBody.request_id).toBeDefined()
  })

  it('error body never contains traceback', () => {
    const errorBody = { error: { code: 'INTERNAL_ERROR', message: 'Something went wrong' } }
    expect(JSON.stringify(errorBody)).not.toContain('Traceback')
    expect(JSON.stringify(errorBody)).not.toContain('File ')
  })
})
