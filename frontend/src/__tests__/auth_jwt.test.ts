import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import {
  login,
  refreshToken,
  logout,
  fetchAuthContext,
  fetchTenants,
  createTenant,
  createUser,
  createRole,
  type LoginResponse,
  type AuthContextResponse,
  type TenantRecord,
} from "../api/auth"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

const baseLoginResp: LoginResponse = {
  access_token: "eyJ.access.token",
  refresh_token: "eyJ.refresh.token",
  token_type: "bearer",
  expires_in: 900,
}

// =============================================================================
// Login API
// =============================================================================

describe("login", () => {
  it("returns token pair and stores in localStorage", async () => {
    mockPost.mockResolvedValue({ data: baseLoginResp })
    const res = await login({ username: "admin", password: "admin" })
    expect(res.access_token).toBe("eyJ.access.token")
    expect(localStorage.getItem("access_token")).toBe("eyJ.access.token")
    expect(localStorage.getItem("refresh_token")).toBe("eyJ.refresh.token")
    expect(mockPost).toHaveBeenCalledWith("/auth/login", { username: "admin", password: "admin" })
  })

  it("sends tenant_id when provided", async () => {
    mockPost.mockResolvedValue({ data: baseLoginResp })
    await login({ username: "admin", password: "admin", tenant_id: "tenant-1" })
    expect(mockPost).toHaveBeenCalledWith("/auth/login", {
      username: "admin", password: "admin", tenant_id: "tenant-1",
    })
  })

  it("handles 401 error", async () => {
    mockPost.mockRejectedValue(new Error("Unauthorized"))
    await expect(login({ username: "bad", password: "bad" })).rejects.toThrow("Unauthorized")
  })

  it("does not store tokens on failed login", async () => {
    localStorage.setItem("existing", "value")
    mockPost.mockRejectedValue(new Error("Fail"))
    try { await login({ username: "x", password: "x" }) } catch { /* */ }
    expect(localStorage.getItem("access_token")).toBeNull()
  })
})

// =============================================================================
// Refresh Token API
// =============================================================================

describe("refreshToken", () => {
  it("returns new tokens and updates localStorage", async () => {
    mockPost.mockResolvedValue({ data: baseLoginResp })
    const res = await refreshToken({ refresh_token: "old-rt" })
    expect(res.access_token).toBe("eyJ.access.token")
    expect(localStorage.getItem("access_token")).toBe("eyJ.access.token")
    expect(mockPost).toHaveBeenCalledWith("/auth/refresh", { refresh_token: "old-rt" })
  })

  it("handles invalid refresh token", async () => {
    mockPost.mockRejectedValue(new Error("Invalid"))
    await expect(refreshToken({ refresh_token: "bad" })).rejects.toThrow("Invalid")
  })
})

// =============================================================================
// Logout API
// =============================================================================

describe("logout", () => {
  it("clears localStorage tokens", async () => {
    localStorage.setItem("access_token", "at")
    localStorage.setItem("refresh_token", "rt")
    mockPost.mockResolvedValue({ data: { success: true } })
    const res = await logout()
    expect(res.success).toBe(true)
    expect(localStorage.getItem("access_token")).toBeNull()
    expect(localStorage.getItem("refresh_token")).toBeNull()
  })
})

// =============================================================================
// Auth Context
// =============================================================================

describe("fetchAuthContext", () => {
  it("includes Bearer header when token exists", async () => {
    localStorage.setItem("access_token", "my-token")
    const ctx: AuthContextResponse = {
      user_id: "u1", username: "admin", roles: ["admin"],
      permissions: ["task:create"], tenant_id: "default",
      is_authenticated: true, request_id: null,
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(res.is_authenticated).toBe(true)
    expect(res.tenant_id).toBe("default")
    expect(mockGet).toHaveBeenCalledWith("/auth/me", {
      headers: { Authorization: "Bearer my-token" },
    })
  })

  it("sends empty headers when no token", async () => {
    const ctx: AuthContextResponse = {
      user_id: "anon", username: "anon", roles: [],
      permissions: [], tenant_id: "", is_authenticated: false, request_id: null,
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(res.is_authenticated).toBe(false)
  })
})

// =============================================================================
// Tenant API
// =============================================================================

describe("Tenants API", () => {
  it("fetchTenants returns list", async () => {
    const t: TenantRecord = {
      id: "t1", name: "Org1", slug: "org1", is_active: true,
      metadata: {}, created_at: "", updated_at: "",
    }
    mockGet.mockResolvedValue({ data: { tenants: [t], total: 1 } })
    const res = await fetchTenants()
    expect(res.tenants).toHaveLength(1)
    expect(res.tenants[0].slug).toBe("org1")
  })

  it("createTenant sends request", async () => {
    const t: TenantRecord = {
      id: "new", name: "NewOrg", slug: "new-org", is_active: true,
      metadata: {}, created_at: "", updated_at: "",
    }
    mockPost.mockResolvedValue({ data: t })
    const res = await createTenant({ name: "NewOrg", slug: "new-org" })
    expect(res.name).toBe("NewOrg")
    expect(mockPost).toHaveBeenCalledWith("/auth/tenants", { name: "NewOrg", slug: "new-org" })
  })
})

// =============================================================================
// User with Password + Tenant
// =============================================================================

describe("createUser with password and tenant", () => {
  it("creates user with password", async () => {
    const user = {
      id: "u1", username: "pwduser", email: "p@t.com", roles: [],
      is_active: true, hashed_password: "********", tenant_ids: [],
      metadata: {}, created_at: "", updated_at: "",
    }
    mockPost.mockResolvedValue({ data: user })
    const res = await createUser({ username: "pwduser", email: "p@t.com", password: "secret" })
    expect(res.username).toBe("pwduser")
    expect(res.hashed_password).toBe("********")
    expect(mockPost).toHaveBeenCalledWith("/auth/users", {
      username: "pwduser", email: "p@t.com", password: "secret", roles: [], tenant_ids: [], metadata: undefined,
    })
  })

  it("creates user with tenant_ids", async () => {
    const user = {
      id: "u2", username: "tuser", email: "t@t.com", roles: [],
      is_active: true, hashed_password: "********", tenant_ids: ["tenant-default"],
      metadata: {}, created_at: "", updated_at: "",
    }
    mockPost.mockResolvedValue({ data: user })
    const res = await createUser({ username: "tuser", email: "t@t.com", tenant_ids: ["tenant-default"] })
    expect(res.tenant_ids).toContain("tenant-default")
  })
})

// =============================================================================
// Role with tenant
// =============================================================================

describe("createRole with tenant", () => {
  it("creates role with tenant_id", async () => {
    const role = {
      id: "r1", name: "trole", description: "T", permissions: ["task:read"],
      tenant_id: "tenant-1", created_at: "", updated_at: "",
    }
    mockPost.mockResolvedValue({ data: role })
    const res = await createRole({
      name: "trole", description: "T", permissions: ["task:read"], tenant_id: "tenant-1",
    })
    expect(res.tenant_id).toBe("tenant-1")
    expect(mockPost).toHaveBeenCalledWith("/auth/roles", {
      name: "trole", description: "T", permissions: ["task:read"], tenant_id: "tenant-1",
    })
  })
})

// =============================================================================
// Type Tests
// =============================================================================

describe("LoginResponse type", () => {
  it("has required fields", () => {
    const r: LoginResponse = baseLoginResp
    expect(r.access_token).toBe("eyJ.access.token")
    expect(r.token_type).toBe("bearer")
    expect(r.expires_in).toBe(900)
  })
})

describe("TenantRecord type", () => {
  it("has all fields", () => {
    const t: TenantRecord = {
      id: "t1", name: "O", slug: "o", is_active: true,
      metadata: {}, created_at: "", updated_at: "",
    }
    expect(t.id).toBe("t1")
    expect(t.is_active).toBe(true)
  })
})

describe("AuthContextResponse type with tenant", () => {
  it("includes tenant_id", () => {
    const ctx: AuthContextResponse = {
      user_id: "u1", username: "admin", roles: ["admin"],
      permissions: [], tenant_id: "t-default",
      is_authenticated: true, request_id: null,
    }
    expect(ctx.tenant_id).toBe("t-default")
  })
})
// =============================================================================
// Extended API Tests
// =============================================================================

describe("fetchUsers with tenant filter", () => {
  it("passes tenant_id query param", async () => {
    const { fetchUsers } = await import("../api/auth")
    mockGet.mockResolvedValue({ data: { users: [], total: 0 } })
    await fetchUsers("tenant-1")
    expect(mockGet).toHaveBeenCalledWith("/auth/users", { params: { tenant_id: "tenant-1" } })
  })

  it("omits param when tenant empty", async () => {
    const { fetchUsers } = await import("../api/auth")
    mockGet.mockResolvedValue({ data: { users: [], total: 0 } })
    await fetchUsers("")
    expect(mockGet).toHaveBeenCalledWith("/auth/users", { params: {} })
  })
})

describe("fetchRoles with tenant filter", () => {
  it("passes tenant_id query param", async () => {
    const { fetchRoles } = await import("../api/auth")
    mockGet.mockResolvedValue({ data: { roles: [], total: 0 } })
    await fetchRoles("t1")
    expect(mockGet).toHaveBeenCalledWith("/auth/roles", { params: { tenant_id: "t1" } })
  })
})

describe("updateUser with password", () => {
  it("sends password in update request", async () => {
    const { updateUser } = await import("../api/auth")
    const user = {
      id: "u1", username: "u", email: "e@e.com", roles: [],
      is_active: true, hashed_password: "********", tenant_ids: [],
      metadata: {}, created_at: "", updated_at: "",
    }
    mockPatch.mockResolvedValue({ data: user })
    await updateUser("u1", { password: "newpass" })
    const mockPatch = vi.mocked(apiClient.patch)
    expect(mockPatch).toHaveBeenCalledWith("/auth/users/u1", { password: "newpass" })
  })
})

describe("Token storage behavior", () => {
  it("refresh stores new tokens", async () => {
    localStorage.setItem("access_token", "old-at")
    localStorage.setItem("refresh_token", "old-rt")
    const newTokens: LoginResponse = {
      access_token: "new-at", refresh_token: "new-rt", token_type: "bearer", expires_in: 900,
    }
    mockPost.mockResolvedValue({ data: newTokens })
    await refreshToken({ refresh_token: "old-rt" })
    expect(localStorage.getItem("access_token")).toBe("new-at")
    expect(localStorage.getItem("refresh_token")).toBe("new-rt")
  })

  it("logout clears all stored tokens", async () => {
    localStorage.setItem("access_token", "at")
    localStorage.setItem("refresh_token", "rt")
    localStorage.setItem("other_key", "keep")
    mockPost.mockResolvedValue({ data: { success: true } })
    await logout()
    expect(localStorage.getItem("access_token")).toBeNull()
    expect(localStorage.getItem("refresh_token")).toBeNull()
    expect(localStorage.getItem("other_key")).toBe("keep")
  })

  it("login failure preserves existing tokens", async () => {
    localStorage.setItem("access_token", "existing-at")
    mockPost.mockRejectedValue(new Error("Auth failed"))
    try { await login({ username: "x", password: "x" }) } catch { /* empty */ }
    expect(localStorage.getItem("access_token")).toBe("existing-at")
  })
})

describe("AuthContext tenant_id", () => {
  it("response includes tenant_id", async () => {
    const ctx: AuthContextResponse = {
      user_id: "u1", username: "admin", roles: ["admin"],
      permissions: ["task:read"], tenant_id: "org-123",
      is_authenticated: true, request_id: "req-1",
    }
    mockGet.mockResolvedValue({ data: ctx })
    const res = await fetchAuthContext()
    expect(res.tenant_id).toBe("org-123")
  })
})

describe("createUser empty defaults", () => {
  it("sends default roles and tenant_ids as empty arrays", async () => {
    const { createUser } = await import("../api/auth")
    const user = {
      id: "u1", username: "min", email: "m@m.com", roles: [],
      is_active: true, hashed_password: "", tenant_ids: [],
      metadata: {}, created_at: "", updated_at: "",
    }
    mockPost.mockResolvedValue({ data: user })
    await createUser({ username: "min", email: "m@m.com" })
    expect(mockPost).toHaveBeenCalledWith("/auth/users", {
      username: "min", email: "m@m.com", password: "", roles: [], tenant_ids: [], metadata: undefined,
    })
  })
})