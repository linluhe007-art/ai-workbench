import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAuthContext,
  fetchUsers,
  fetchUser,
  createUser,
  updateUser,
  deleteUser,
  fetchUserPermissions,
  fetchRoles,
  fetchRole,
  createRole,
  updateRole,
  deleteRole,
  fetchAllPermissions,
} from '../api/auth'
import type { UserCreateRequest, UserUpdateRequest, RoleCreateRequest, RoleUpdateRequest } from '../api/auth'

// Auth Context
export function useAuthContext() {
  return useQuery({
    queryKey: ['auth-context'],
    queryFn: fetchAuthContext,
    staleTime: 60000,
  })
}

// Users
export function useUsers() {
  return useQuery({
    queryKey: ['auth-users'],
    queryFn: fetchUsers,
  })
}

export function useUser(userId: string | null) {
  return useQuery({
    queryKey: ['auth-user', userId],
    queryFn: () => fetchUser(userId!),
    enabled: !!userId,
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: UserCreateRequest) => createUser(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-users'] })
    },
  })
}

export function useUpdateUser(userId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: UserUpdateRequest) => updateUser(userId!, req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-users'] })
      qc.invalidateQueries({ queryKey: ['auth-user', userId] })
    },
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-users'] })
    },
  })
}

export function useUserPermissions(userId: string | null) {
  return useQuery({
    queryKey: ['auth-user-permissions', userId],
    queryFn: () => fetchUserPermissions(userId!),
    enabled: !!userId,
  })
}

// Roles
export function useRoles() {
  return useQuery({
    queryKey: ['auth-roles'],
    queryFn: fetchRoles,
  })
}

export function useRole(roleId: string | null) {
  return useQuery({
    queryKey: ['auth-role', roleId],
    queryFn: () => fetchRole(roleId!),
    enabled: !!roleId,
  })
}

export function useCreateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: RoleCreateRequest) => createRole(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-roles'] })
    },
  })
}

export function useUpdateRole(roleId: string | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: RoleUpdateRequest) => updateRole(roleId!, req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-roles'] })
      qc.invalidateQueries({ queryKey: ['auth-role', roleId] })
    },
  })
}

export function useDeleteRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (roleId: string) => deleteRole(roleId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth-roles'] })
    },
  })
}

export function useAllPermissions() {
  return useQuery({
    queryKey: ['auth-permissions'],
    queryFn: fetchAllPermissions,
    staleTime: 300000,
  })
}