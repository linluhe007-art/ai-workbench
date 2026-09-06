import apiClient from './client'

export interface UserRecord {
  id: string
  username: string
  email: string
  roles: string[]
  is_active: boolean
  hashed_password: string
  tenant_ids: string[]
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface RoleRecord {
  id: string
  name: string
  description: string
  permissions: string[]
  tenant_id: string
  created_at: string
  updated_at: string
}

export interface TenantRecord {
  id: string
  name: string
  slug: string
  is_active: boolean
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AuthContextResponse {
  user_id: string
  username: string
  roles: string[]
  permissions: string[]
  tenant_id: string
  is_authenticated: boolean
  request_id: string | null
}

export interface PermissionInfo {
  key: string
  name: string
}

export interface LoginRequest {
  username: string
  password: string
  tenant_id?: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RefreshRequest {
  refresh_token: string
}

export interface UserCreateRequest {
  username: string
  email: string
  password?: string
  roles?: string[]
  tenant_ids?: string[]
  metadata?: Record<string, unknown>
}

export interface UserUpdateRequest {
  username?: string
  email?: string
  password?: string
  roles?: string[]
  is_active?: boolean
  tenant_ids?: string[]
  metadata?: Record<string, unknown>
}

export interface RoleCreateRequest {
  name: string
  description: string
  permissions?: string[]
  tenant_id?: string
}

export interface RoleUpdateRequest {
  name?: string
  description?: string
  permissions?: string[]
}

export interface TenantCreateRequest {
  name: string
  slug?: string
  metadata?: Record<string, unknown>
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  if (token) {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}

// Auth
export async function login(req: LoginRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post('/auth/login', req)
  if (data.access_token) {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }
  return data
}

export async function refreshToken(req: RefreshRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post('/auth/refresh', req)
  if (data.access_token) {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }
  return data
}

export async function logout(): Promise<{ success: boolean }> {
  const { data } = await apiClient.post('/auth/logout')
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  return data
}

export async function fetchAuthContext(): Promise<AuthContextResponse> {
  const { data } = await apiClient.get('/auth/me', { headers: getAuthHeader() })
  return data
}

// Tenants
export async function fetchTenants(): Promise<{ tenants: TenantRecord[]; total: number }> {
  const { data } = await apiClient.get('/auth/tenants')
  return data
}

export async function createTenant(req: TenantCreateRequest): Promise<TenantRecord> {
  const { data } = await apiClient.post('/auth/tenants', req)
  return data
}

// Users
export async function fetchUsers(tenantId = ''): Promise<{ users: UserRecord[]; total: number }> {
  const { data } = await apiClient.get('/auth/users', { params: tenantId ? { tenant_id: tenantId } : {} })
  return data
}

export async function fetchUser(userId: string): Promise<UserRecord> {
  const { data } = await apiClient.get(`/auth/users/${userId}`)
  return data
}

export async function createUser(req: UserCreateRequest): Promise<UserRecord> {
  const { data } = await apiClient.post('/auth/users', req)
  return data
}

export async function updateUser(userId: string, req: UserUpdateRequest): Promise<UserRecord> {
  const { data } = await apiClient.patch(`/auth/users/${userId}`, req)
  return data
}

export async function deleteUser(userId: string): Promise<{ deleted: boolean; user_id: string }> {
  const { data } = await apiClient.delete(`/auth/users/${userId}`)
  return data
}

export async function fetchUserPermissions(userId: string): Promise<{
  user_id: string; username: string; roles: string[]; permissions: string[]
}> {
  const { data } = await apiClient.get(`/auth/users/${userId}/permissions`)
  return data
}

// Roles
export async function fetchRoles(tenantId = ''): Promise<{ roles: RoleRecord[]; total: number }> {
  const { data } = await apiClient.get('/auth/roles', { params: tenantId ? { tenant_id: tenantId } : {} })
  return data
}

export async function fetchRole(roleId: string): Promise<RoleRecord> {
  const { data } = await apiClient.get(`/auth/roles/${roleId}`)
  return data
}

export async function createRole(req: RoleCreateRequest): Promise<RoleRecord> {
  const { data } = await apiClient.post('/auth/roles', req)
  return data
}

export async function updateRole(roleId: string, req: RoleUpdateRequest): Promise<RoleRecord> {
  const { data } = await apiClient.patch(`/auth/roles/${roleId}`, req)
  return data
}

export async function deleteRole(roleId: string): Promise<{ deleted: boolean; role_id: string }> {
  const { data } = await apiClient.delete(`/auth/roles/${roleId}`)
  return data
}

// Permissions
export async function fetchAllPermissions(): Promise<{ permissions: PermissionInfo[] }> {
  const { data } = await apiClient.get('/auth/permissions')
  return data
}

export async function checkPermission(permission: string): Promise<{
  permission: string; has_permission: boolean; user_id: string; is_authenticated: boolean
}> {
  const { data } = await apiClient.get('/auth/permissions/check', { params: { permission } })
  return data
}