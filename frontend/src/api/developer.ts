import apiClient from './client'

export interface APIKeyInfo {
  id: string
  name: string
  key_prefix: string
  permissions: string[]
  tenant_id: string
  enabled: boolean
  last_used_at: string | null
  created_at: string
}

export interface CreateAPIKeyResponse {
  api_key: APIKeyInfo
  raw_key: string
}

export interface APIKeyListResponse {
  api_keys: APIKeyInfo[]
  total: number
}

export interface WebhookInfo {
  id: string
  url: string
  events: string[]
  tenant_id: string
  enabled: boolean
  created_at: string
  last_delivery_at: string | null
  delivery_count: number
  failure_count: number
}

export interface WebhookListResponse {
  webhooks: WebhookInfo[]
  total: number
}

export const createAPIKey = (name: string, permissions: string[] = ['read']) =>
  apiClient.post<CreateAPIKeyResponse>('/api-keys', { name, permissions }).then((r) => r.data)

export const fetchAPIKeys = () =>
  apiClient.get<APIKeyListResponse>('/api-keys').then((r) => r.data)

export const deleteAPIKey = (keyId: string) =>
  apiClient.delete(`/api-keys/${keyId}`).then((r) => r.data)

export const createWebhook = (url: string, events?: string[]) =>
  apiClient.post('/webhooks', { url, events }).then((r) => r.data)

export const fetchWebhooks = () =>
  apiClient.get<WebhookListResponse>('/webhooks').then((r) => r.data)

export const deleteWebhook = (id: string) =>
  apiClient.delete(`/webhooks/${id}`).then((r) => r.data)