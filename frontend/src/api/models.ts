import apiClient from './client'

export interface ProviderInfo {
  type: string
  description: string
}

export interface ProvidersResponse {
  success: boolean
  providers: ProviderInfo[]
}

export interface RoutingTableEntry {
  provider_type: string
  model_name: string
  reason: string
  privacy_level: string
  estimated_cost: string
}

export interface ModelConfigInfo {
  provider_type: string
  endpoint: string
  api_key_set: boolean
  enabled: boolean
  priority: number
}

export interface AvailableModel {
  name: string
  provider: string
  task_categories: string[]
  privacy_level: string
  estimated_cost: string
}

export interface ModelsListResponse {
  success: boolean
  routing_table: Record<string, RoutingTableEntry>
  configs: ModelConfigInfo[]
  available_models: AvailableModel[]
}

export interface ConfigureRequest {
  provider_type: string
  endpoint?: string
  api_key?: string
  priority?: number
}

export interface TestResponse {
  success: boolean
  provider_type: string
  connected: boolean
  message: string
}

export interface GenerateRequest {
  task_category: string
  prompt: string
  privacy_level?: string
}

export interface GenerateResponse {
  success: boolean
  routing: RoutingTableEntry
  response: { text: string; model: string; usage: Record<string, unknown>; error: string }
}

export const fetchModels = () =>
  apiClient.get<ModelsListResponse>('/models').then((r) => r.data)

export const fetchProviders = () =>
  apiClient.get<ProvidersResponse>('/models/providers').then((r) => r.data)

export const configureModel = (req: ConfigureRequest) =>
  apiClient.post('/models/configure', req).then((r) => r.data)

export const testModel = (providerType: string) =>
  apiClient.post<TestResponse>('/models/test', { provider_type: providerType }).then((r) => r.data)

export const generateWithModel = (req: GenerateRequest) =>
  apiClient.post<GenerateResponse>('/models/generate', req).then((r) => r.data)
