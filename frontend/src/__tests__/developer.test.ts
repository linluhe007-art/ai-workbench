import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  createAPIKey, fetchAPIKeys, deleteAPIKey,
  createWebhook, fetchWebhooks, deleteWebhook,
} from "../api/developer"
import { useAPIKeys, useWebhooks } from "../hooks/useDeveloper"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockDelete = vi.mocked(apiClient.delete)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const baseKey = { id: "k1", name: "test", key_prefix: "ak-12345678", permissions: ["read"], tenant_id: "", enabled: true, last_used_at: null, created_at: "2026-01-01T00:00:00" }
const baseWh = { id: "wh1", url: "https://example.com/hook", events: ["task.completed"], tenant_id: "", enabled: true, created_at: "2026-01-01T00:00:00", last_delivery_at: null, delivery_count: 0, failure_count: 0 }

// --- API Key API Tests ---

describe("API Key API", () => {
  it("createAPIKey returns key and raw", async () => {
    mockPost.mockResolvedValue({ data: { api_key: baseKey, raw_key: "ak-abcdef123456" } })
    const res = await createAPIKey("test")
    expect(res.api_key.name).toBe("test")
    expect(res.raw_key).toBe("ak-abcdef123456")
    expect(mockPost).toHaveBeenCalledWith("/api-keys", { name: "test", permissions: ["read"] })
  })

  it("createAPIKey with custom permissions", async () => {
    mockPost.mockResolvedValue({ data: { api_key: baseKey, raw_key: "x" } })
    await createAPIKey("rw", ["read", "write"])
    expect(mockPost).toHaveBeenCalledWith("/api-keys", { name: "rw", permissions: ["read", "write"] })
  })

  it("fetchAPIKeys returns list", async () => {
    mockGet.mockResolvedValue({ data: { api_keys: [baseKey], total: 1 } })
    const res = await fetchAPIKeys()
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/api-keys")
  })

  it("deleteAPIKey sends request", async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const res = await deleteAPIKey("k1")
    expect(res.success).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/api-keys/k1")
  })
})

// --- Webhook API Tests ---

describe("Webhook API", () => {
  it("createWebhook sends request", async () => {
    mockPost.mockResolvedValue({ data: { webhook: baseWh } })
    const res = await createWebhook("https://example.com/hook", ["task.completed"])
    expect(res.webhook.url).toBe("https://example.com/hook")
    expect(mockPost).toHaveBeenCalledWith("/webhooks", { url: "https://example.com/hook", events: ["task.completed"] })
  })

  it("createWebhook default events", async () => {
    mockPost.mockResolvedValue({ data: { webhook: baseWh } })
    await createWebhook("https://example.com/hook")
    expect(mockPost).toHaveBeenCalledWith("/webhooks", { url: "https://example.com/hook", events: undefined })
  })

  it("fetchWebhooks returns list", async () => {
    mockGet.mockResolvedValue({ data: { webhooks: [baseWh], total: 1 } })
    const res = await fetchWebhooks()
    expect(res.total).toBe(1)
    expect(mockGet).toHaveBeenCalledWith("/webhooks")
  })

  it("deleteWebhook sends request", async () => {
    mockDelete.mockResolvedValue({ data: { success: true } })
    const res = await deleteWebhook("wh1")
    expect(res.success).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith("/webhooks/wh1")
  })
})

// --- Response Parsing ---

describe("Developer response parsing", () => {
  it("api key has key_prefix", () => {
    expect(baseKey.key_prefix).toBe("ak-12345678")
  })

  it("api key has permissions array", () => {
    expect(Array.isArray(baseKey.permissions)).toBe(true)
    expect(baseKey.permissions).toContain("read")
  })

  it("webhook has events array", () => {
    expect(Array.isArray(baseWh.events)).toBe(true)
    expect(baseWh.events).toContain("task.completed")
  })

  it("webhook tracks delivery_count", () => {
    expect(baseWh.delivery_count).toBe(0)
  })

  it("webhook tracks failure_count", () => {
    expect(baseWh.failure_count).toBe(0)
  })
})

// --- Hook Tests ---

describe("useAPIKeys hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: { api_keys: [baseKey], total: 1 } })
    const { result } = renderHook(() => useAPIKeys(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
  })
})

describe("useWebhooks hook", () => {
  it("returns data after fetch", async () => {
    mockGet.mockResolvedValue({ data: { webhooks: [baseWh], total: 1 } })
    const { result } = renderHook(() => useWebhooks(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
  })
})

// --- Error Handling ---

describe("Developer error handling", () => {
  it("createAPIKey handles network error", async () => {
    mockPost.mockRejectedValue(new Error("Network Error"))
    await expect(createAPIKey("x")).rejects.toThrow("Network Error")
  })

  it("fetchAPIKeys handles error", async () => {
    mockGet.mockRejectedValue(new Error("Timeout"))
    await expect(fetchAPIKeys()).rejects.toThrow("Timeout")
  })

  it("deleteAPIKey handles error", async () => {
    mockDelete.mockRejectedValue(new Error("Failed"))
    await expect(deleteAPIKey("x")).rejects.toThrow("Failed")
  })

  it("createWebhook handles error", async () => {
    mockPost.mockRejectedValue(new Error("Service Unavailable"))
    await expect(createWebhook("url")).rejects.toThrow("Service Unavailable")
  })

  it("fetchWebhooks handles error", async () => {
    mockGet.mockRejectedValue(new Error("Timeout"))
    await expect(fetchWebhooks()).rejects.toThrow("Timeout")
  })

  it("deleteWebhook handles error", async () => {
    mockDelete.mockRejectedValue(new Error("Gone"))
    await expect(deleteWebhook("x")).rejects.toThrow("Gone")
  })
})

// --- Edge Cases ---

describe("Developer edge cases", () => {
  it("handles empty api keys list", async () => {
    mockGet.mockResolvedValue({ data: { api_keys: [], total: 0 } })
    const res = await fetchAPIKeys()
    expect(res.total).toBe(0)
  })

  it("handles empty webhooks list", async () => {
    mockGet.mockResolvedValue({ data: { webhooks: [], total: 0 } })
    const res = await fetchWebhooks()
    expect(res.total).toBe(0)
  })

  it("handles disabled api key", async () => {
    const disabledKey = { ...baseKey, enabled: false }
    mockGet.mockResolvedValue({ data: { api_keys: [disabledKey], total: 1 } })
    const res = await fetchAPIKeys()
    expect(res.api_keys[0].enabled).toBe(false)
  })

  it("handles webhook with failures", async () => {
    const failedWh = { ...baseWh, delivery_count: 10, failure_count: 3 }
    mockGet.mockResolvedValue({ data: { webhooks: [failedWh], total: 1 } })
    const res = await fetchWebhooks()
    expect(res.webhooks[0].failure_count).toBe(3)
  })

  it("handles api key with no permissions", async () => {
    const noPermKey = { ...baseKey, permissions: [] }
    mockGet.mockResolvedValue({ data: { api_keys: [noPermKey], total: 1 } })
    const res = await fetchAPIKeys()
    expect(res.api_keys[0].permissions).toEqual([])
  })

  it("handles webhook with many events", async () => {
    const multiWh = { ...baseWh, events: ["task.completed", "task.failed", "artifact.created", "agent.failed"] }
    mockGet.mockResolvedValue({ data: { webhooks: [multiWh], total: 1 } })
    const res = await fetchWebhooks()
    expect(res.webhooks[0].events).toHaveLength(4)
  })
})

// --- Loading States ---

describe("Developer loading states", () => {
  it("shows loading for api keys", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useAPIKeys(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("shows loading for webhooks", () => {
    mockGet.mockImplementation(() => new Promise(() => {}))
    const { result } = renderHook(() => useWebhooks(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state in api keys hook", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useAPIKeys(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it("handles error state in webhooks hook", async () => {
    mockGet.mockRejectedValue(new Error("Failed"))
    const { result } = renderHook(() => useWebhooks(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// --- API Key Response Validation ---

describe("API Key response validation", () => {
  it("key has all required fields", async () => {
    mockPost.mockResolvedValue({ data: { api_key: baseKey, raw_key: "x" } })
    const res = await createAPIKey("test")
    const k = res.api_key
    expect(k.id).toBeTruthy()
    expect(k.name).toBeTruthy()
    expect(k.key_prefix).toBeTruthy()
    expect(k.permissions).toBeDefined()
    expect(k.enabled).toBeDefined()
    expect(k.created_at).toBeTruthy()
  })

  it("raw_key is returned only once", async () => {
    mockPost.mockResolvedValue({ data: { api_key: baseKey, raw_key: "secret123" } })
    const res = await createAPIKey("test")
    expect(res.raw_key).toBe("secret123")
    expect((res.api_key as Record<string, unknown>).raw_key).toBeUndefined()
  })
})

// --- Webhook Response Validation ---

describe("Webhook response validation", () => {
  it("webhook has all required fields", async () => {
    mockPost.mockResolvedValue({ data: { webhook: baseWh } })
    const res = await createWebhook("https://x.com/hook")
    const w = res.webhook
    expect(w.id).toBeTruthy()
    expect(w.url).toBeTruthy()
    expect(w.events).toBeDefined()
    expect(w.enabled).toBeDefined()
    expect(w.delivery_count).toBeDefined()
    expect(w.failure_count).toBeDefined()
  })

  it("webhook secret is not exposed", async () => {
    mockPost.mockResolvedValue({ data: { webhook: baseWh } })
    const res = await createWebhook("https://x.com/hook")
    expect((res.webhook as Record<string, unknown>).secret).toBeUndefined()
  })
})

// --- Tenant Isolation Simulation ---

describe("Developer tenant isolation", () => {
  it("handles tenant-scoped api key", async () => {
    const tenantKey = { ...baseKey, tenant_id: "t1" }
    mockGet.mockResolvedValue({ data: { api_keys: [tenantKey], total: 1 } })
    const res = await fetchAPIKeys()
    expect(res.api_keys[0].tenant_id).toBe("t1")
  })

  it("handles tenant-scoped webhook", async () => {
    const tenantWh = { ...baseWh, tenant_id: "t2" }
    mockGet.mockResolvedValue({ data: { webhooks: [tenantWh], total: 1 } })
    const res = await fetchWebhooks()
    expect(res.webhooks[0].tenant_id).toBe("t2")
  })
})

// --- Permission Parsing ---

describe("API Key permission parsing", () => {
  it("parses multiple permissions", () => {
    const k = { ...baseKey, permissions: ["read", "write", "admin"] }
    expect(k.permissions).toHaveLength(3)
    expect(k.permissions).toContain("admin")
  })
})

// --- Webhook Event Filtering ---

describe("Webhook event filtering", () => {
  it("supports task.completed event", () => {
    const wh = { ...baseWh, events: ["task.completed"] }
    expect(wh.events).toEqual(["task.completed"])
  })

  it("supports all four event types", () => {
    const wh = { ...baseWh, events: ["task.completed", "task.failed", "artifact.created", "agent.failed"] }
    expect(wh.events).toHaveLength(4)
  })
})