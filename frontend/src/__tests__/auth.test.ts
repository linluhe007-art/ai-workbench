import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
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
  checkPermission,
  type AuthContextResponse,
  type UserRecord,
  type RoleRecord,
} from "../api/auth"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockPatch = vi.mocked(apiClient.patch)
const mockDelete = vi.mocked(apiClient.delete)

beforeEach(() => vi.clearAllMocks())

const baseUser: UserRecord = {
  id: "u1", username: "admin", email: "admin@test.com",
  roles: ["role-admin"], is_active: true,
  metadata: {}, created_at: "2026-08-12T10:00:00Z", updated_at: "2026-08-12T10:00:00Z",
}

const baseRole: RoleRecord = {
  id: "r1", name: "viewer", description: "Viewer role",
  permissions: ["task:read", "agent:read"],
  created_at: "2026-08-12T10:00:00Z", updated_at: "2026-08-12T10:00:00Z",
}

// =============================================================================
// Auth Context API
// =============================================================================

describe("fetchAuthContext", () => {
  it("returns auth context", async () => {
    const ctx: AuthContextResponse = {
      user_id: "u1", username: "admin", roles: ["admin"],
      permissions: ["task:create"], is_authenticated: true, request_id: null,
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(res.is_authenticated).toBe(true)
    expect(res.username).toBe("admin")
  })

  it("returns anonymous context", async () => {
    const ctx: AuthContextResponse = {
      user_id: "anonymous", username: "anonymous", roles: [],
      permissions: [], is_authenticated: false, request_id: null,
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(res.is_authenticated).toBe(false)
  })

  it("handles network error", async () => {
    mockGet.mockRejectedValue(new Error("Network Error"))
    await expect(fetchAuthContext()).rejects.toThrow("Network Error")
  })

  it("has all required fields", async () => {
    const ctx: AuthContextResponse = {
      user_id: "uid", username: "uname", roles: ["r1"],
      permissions: ["p1"], is_authenticated: true, request_id: "rid",
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(Object.keys(res)).toHaveLength(6)
  })
})

// =============================================================================
// Users API
// =============================================================================

describe("fetchUsers", () => {
  it("returns users list", async () => {
    mockGet.mockResolvedValue({ data: { users: [baseUser], total: 1 } })
    const res = await fetchUsers()
    expect(res.users).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/auth/users")
  })

  it("handles empty list", async () => {
    mockGet.mockResolvedValue({ data: { users: [], total: 0 } })
    const res = await fetchUsers()
    expect(res.users).toHaveLength(0)
  })

  it("response has correct shape", async () => {
    mockGet.mockResolvedValue({ data: { users: [baseUser], total: 1 } })
    const res = await fetchUsers()
    expect(res).toHaveProperty("users")
    expect(res).toHaveProperty("total")
    expect(Array.isArray(res.users)).toBe(true)
    expect(typeof res.total).toBe("number")
  })
})

describe("fetchUser", () => {
  it("returns single user", async () => {
    mockGet.mockResolvedValue({ data: baseUser })
    const res = await fetchUser("u1")
    expect(res.username).toBe("admin")
    expect(res.id).toBe("u1")
  })

  it("handles 404", async () => {
    mockGet.mockRejectedValue(new Error("Not Found"))
    await expect(fetchUser("nonexistent")).rejects.toThrow("Not Found")
  })
})

describe("createUser", () => {
  it("creates a user", async () => {
    mockPost.mockResolvedValue({ data: baseUser })
    const res = await createUser({ username: "admin", email: "a@b.com" })
    expect(res.username).toBe("admin")
    expect(mockPost).toHaveBeenCalledWith("/auth/users", { username: "admin", email: "a@b.com" })
  })

  it("creates user with roles", async () => {
    mockPost.mockResolvedValue({ data: { ...baseUser, roles: ["role-viewer"] } })
    const res = await createUser({ username: "viewer", email: "v@b.com", roles: ["role-viewer"] })
    expect(res.roles).toContain("role-viewer")
  })

  it("handles error", async () => {
    mockPost.mockRejectedValue(new Error("Conflict"))
    await expect(createUser({ username: "dup", email: "d@d.com" })).rejects.toThrow("Conflict")
  })
})

describe("updateUser", () => {
  it("updates a user", async () => {
    mockPatch.mockResolvedValue({ data: { ...baseUser, email: "updated@test.com" } })
    const res = await updateUser("u1", { email: "updated@test.com" })
    expect(res.email).toBe("updated@test.com")
    expect(mockPatch).toHaveBeenCalledWith("/auth/users/u1", { email: "updated@test.com" })
  })

  it("updates is_active", async () => {
    mockPatch.mockResolvedValue({ data: { ...baseUser, is_active: false } })
    const res = await updateUser("u1", { is_active: false })
    expect(res.is_active).toBe(false)
  })

  it("sends all optional fields", async () => {
    mockPatch.mockResolvedValue({ data: { ...baseUser, username: "new", email: "new@t.com", is_active: false, roles: ["role-viewer"] } })
    const res = await updateUser("u1", { username: "new", email: "new@t.com", roles: ["role-viewer"], is_active: false })
    expect(res.username).toBe("new")
    expect(res.is_active).toBe(false)
    expect(mockPatch).toHaveBeenCalledWith("/auth/users/u1", { username: "new", email: "new@t.com", roles: ["role-viewer"], is_active: false })
  })
})

describe("deleteUser", () => {
  it("deletes a user", async () => {
    mockDelete.mockResolvedValue({ data: { deleted: true, user_id: "u1" } })
    const res = await deleteUser("u1")
    expect(res.deleted).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/auth/users/u1")
  })

  it("handles not found", async () => {
    mockDelete.mockRejectedValue(new Error("Not Found"))
    await expect(deleteUser("nonexistent")).rejects.toThrow("Not Found")
  })
})

describe("fetchUserPermissions", () => {
  it("returns user permissions", async () => {
    mockGet.mockResolvedValue({
      data: { user_id: "u1", username: "admin", roles: ["admin"], permissions: ["task:create", "task:read"] },
    })
    const res = await fetchUserPermissions("u1")
    expect(res.permissions).toHaveLength(2)
    expect(res.roles).toContain("admin")
  })

  it("returns empty permissions for user with no roles", async () => {
    mockGet.mockResolvedValue({
      data: { user_id: "u2", username: "noroles", roles: [], permissions: [] },
    })
    const res = await fetchUserPermissions("u2")
    expect(res.permissions).toHaveLength(0)
    expect(res.roles).toHaveLength(0)
  })
})

// =============================================================================
// Roles API
// =============================================================================

describe("fetchRoles", () => {
  it("returns roles list", async () => {
    mockGet.mockResolvedValue({ data: { roles: [baseRole], total: 1 } })
    const res = await fetchRoles()
    expect(res.roles).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/auth/roles")
  })

  it("response has correct shape", async () => {
    mockGet.mockResolvedValue({ data: { roles: [baseRole], total: 1 } })
    const res = await fetchRoles()
    expect(res).toHaveProperty("roles")
    expect(res).toHaveProperty("total")
  })
})

describe("fetchRole", () => {
  it("returns single role", async () => {
    mockGet.mockResolvedValue({ data: baseRole })
    const res = await fetchRole("r1")
    expect(res.name).toBe("viewer")
    expect(mockGet).toHaveBeenCalledWith("/auth/roles/r1")
  })

  it("handles error", async () => {
    mockGet.mockRejectedValue(new Error("Not Found"))
    await expect(fetchRole("nonexistent")).rejects.toThrow("Not Found")
  })
})

describe("createRole", () => {
  it("creates a role", async () => {
    mockPost.mockResolvedValue({ data: baseRole })
    const res = await createRole({ name: "viewer", description: "Viewer", permissions: ["task:read"] })
    expect(res.name).toBe("viewer")
    expect(mockPost).toHaveBeenCalledWith("/auth/roles", { name: "viewer", description: "Viewer", permissions: ["task:read"] })
  })

  it("creates role with multiple permissions", async () => {
    mockPost.mockResolvedValue({
      data: { ...baseRole, permissions: ["task:read", "task:create", "agent:read"] },
    })
    const res = await createRole({ name: "power", description: "Power role", permissions: ["task:read", "task:create", "agent:read"] })
    expect(res.permissions).toHaveLength(3)
  })

  it("creates role with no permissions", async () => {
    mockPost.mockResolvedValue({ data: { ...baseRole, permissions: [] } })
    const res = await createRole({ name: "empty", description: "No perms" })
    expect(res.permissions).toHaveLength(0)
  })
})

describe("updateRole", () => {
  it("updates a role", async () => {
    mockPatch.mockResolvedValue({ data: { ...baseRole, description: "Updated" } })
    const res = await updateRole("r1", { description: "Updated" })
    expect(res.description).toBe("Updated")
  })

  it("updates role permissions", async () => {
    mockPatch.mockResolvedValue({ data: { ...baseRole, permissions: ["task:create"] } })
    const res = await updateRole("r1", { permissions: ["task:create"] })
    expect(res.permissions).toContain("task:create")
  })
})

describe("deleteRole", () => {
  it("deletes a role", async () => {
    mockDelete.mockResolvedValue({ data: { deleted: true, role_id: "r1" } })
    const res = await deleteRole("r1")
    expect(res.deleted).toBe(true)
  })

  it("handles delete error", async () => {
    mockDelete.mockRejectedValue(new Error("Forbidden"))
    await expect(deleteRole("protected-role")).rejects.toThrow("Forbidden")
  })
})

// =============================================================================
// Permissions API
// =============================================================================

describe("fetchAllPermissions", () => {
  it("returns all permissions", async () => {
    mockGet.mockResolvedValue({
      data: { permissions: [{ key: "task:read", name: "TASK_READ" }, { key: "task:create", name: "TASK_CREATE" }] },
    })
    const res = await fetchAllPermissions()
    expect(res.permissions).toHaveLength(2)
    expect(res.permissions[0].key).toBe("task:read")
  })

  it("permissions have correct shape", async () => {
    mockGet.mockResolvedValue({ data: { permissions: [{ key: "task:read", name: "TASK_READ" }] } })
    const res = await fetchAllPermissions()
    expect(res.permissions[0]).toHaveProperty("key")
    expect(res.permissions[0]).toHaveProperty("name")
  })
})

describe("checkPermission", () => {
  it("checks a permission", async () => {
    mockGet.mockResolvedValue({
      data: { permission: "task:read", has_permission: true, user_id: "u1", is_authenticated: true },
    })
    const res = await checkPermission("task:read")
    expect(res.has_permission).toBe(true)
    expect(mockGet).toHaveBeenCalledWith("/auth/permissions/check", { params: { permission: "task:read" } })
  })

  it("returns false for missing permission", async () => {
    mockGet.mockResolvedValue({
      data: { permission: "admin:system", has_permission: false, user_id: "anonymous", is_authenticated: false },
    })
    const res = await checkPermission("admin:system")
    expect(res.has_permission).toBe(false)
  })

  it("passes all query params", async () => {
    mockGet.mockResolvedValue({
      data: { permission: "agent:manage", has_permission: false, user_id: "anonymous", is_authenticated: false },
    })
    await checkPermission("agent:manage")
    expect(mockGet).toHaveBeenCalledWith("/auth/permissions/check", { params: { permission: "agent:manage" } })
  })
})

// =============================================================================
// Type Tests
// =============================================================================

describe("Auth types", () => {
  it("UserRecord has all fields", () => {
    const u: UserRecord = baseUser
    expect(u.id).toBe("u1")
    expect(u.username).toBe("admin")
    expect(u.roles).toContain("role-admin")
    expect(u.is_active).toBe(true)
  })

  it("UserRecord has 8 fields", () => {
    const keys = Object.keys(baseUser)
    expect(keys).toHaveLength(8)
  })

  it("RoleRecord has all fields", () => {
    const r: RoleRecord = baseRole
    expect(r.id).toBe("r1")
    expect(r.name).toBe("viewer")
    expect(r.permissions).toContain("task:read")
  })

  it("AuthContextResponse supports anonymous", () => {
    const ctx: AuthContextResponse = {
      user_id: "anonymous", username: "anonymous", roles: [],
      permissions: [], is_authenticated: false, request_id: null,
    }
    expect(ctx.is_authenticated).toBe(false)
    expect(ctx.permissions).toHaveLength(0)
  })

  it("AuthContextResponse supports authenticated", () => {
    const ctx: AuthContextResponse = {
      user_id: "admin", username: "Admin", roles: ["admin"],
      permissions: ["task:create", "admin:system"], is_authenticated: true, request_id: "req-1",
    }
    expect(ctx.is_authenticated).toBe(true)
    expect(ctx.permissions).toHaveLength(2)
    expect(ctx.request_id).toBe("req-1")
  })

  it("AuthContextResponse has 6 fields", () => {
    const ctx: AuthContextResponse = {
      user_id: "uid", username: "uname", roles: ["r1"],
      permissions: ["p1"], is_authenticated: true, request_id: "rid",
    }
    expect(Object.keys(ctx)).toHaveLength(6)
  })
})

// =============================================================================
// Error Handling
// =============================================================================

describe("API error handling", () => {
  it("handles 403 forbidden", async () => {
    mockGet.mockRejectedValue({ response: { status: 403, data: { error: { code: "FORBIDDEN" } } } })
    await expect(checkPermission("admin:system")).rejects.toBeDefined()
  })

  it("handles 500 server error", async () => {
    mockGet.mockRejectedValue(new Error("Server Error"))
    await expect(fetchUsers()).rejects.toThrow("Server Error")
  })
})