import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import {
  fetchModels, fetchProviders, configureModel, testModel, generateWithModel,
} from "../api/models"
import type { ModelsListResponse, RoutingTableEntry } from "../api/models"
import { useModels, useProviders } from "../hooks/useModels"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const entry: RoutingTableEntry = {
  provider_type: "ollama", model_name: "llama3", reason: "Default",
  privacy_level: "high", estimated_cost: "free",
}

const baseResponse: ModelsListResponse = {
  success: true,
  routing_table: { chat: entry, coding: { ...entry, model_name: "codellama" } },
  configs: [{ provider_type: "ollama", endpoint: "http://localhost:11434", api_key_set: false, enabled: true, priority: 0 }],
  available_models: [{ name: "llama3", provider: "ollama", task_categories: ["chat"], privacy_level: "high", estimated_cost: "free" }],
}

// ===== API Tests =====

describe("Models API", () => {
  it("fetchModels returns full response", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(res.success).toBe(true)
    expect(res.routing_table.chat.model_name).toBe("llama3")
    expect(mockGet).toHaveBeenCalledWith("/models")
  })

  it("fetchProviders returns providers", async () => {
    mockGet.mockResolvedValue({
      data: { success: true, providers: [{ type: "ollama", description: "Ollama" }] },
    })
    const res = await fetchProviders()
    expect(res.providers).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/models/providers")
  })

  it("configureModel sends request", async () => {
    mockPost.mockResolvedValue({ data: { success: true, provider_type: "ollama", message: "OK" } })
    const res = await configureModel({ provider_type: "ollama", endpoint: "http://localhost:11434" })
    expect(res.success).toBe(true)
  })

  it("testModel sends correct request", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, provider_type: "ollama", connected: true, message: "OK" },
    })
    const res = await testModel("ollama")
    expect(res.connected).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/models/test", { provider_type: "ollama" })
  })

  it("testModel returns false on failure", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, provider_type: "llama_cpp", connected: false, message: "Failed" },
    })
    const res = await testModel("llama_cpp")
    expect(res.connected).toBe(false)
  })

  it("generateWithModel sends request", async () => {
    mockPost.mockResolvedValue({
      data: {
        success: true,
        routing: entry,
        response: { text: "Hello!", model: "llama3", usage: {}, error: "" },
      },
    })
    const res = await generateWithModel({ task_category: "chat", prompt: "Hi" })
    expect(res.response.text).toBe("Hello!")
    expect(mockPost).toHaveBeenCalledWith("/models/generate", { task_category: "chat", prompt: "Hi" })
  })

  it("generateWithModel includes privacy", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, routing: entry, response: { text: "x", model: "m", usage: {}, error: "" } },
    })
    await generateWithModel({ task_category: "research", prompt: "Test", privacy_level: "high" })
    expect(mockPost).toHaveBeenCalledWith("/models/generate", {
      task_category: "research", prompt: "Test", privacy_level: "high",
    })
  })
})

// ===== Response Parsing =====

describe("Models Response Parsing", () => {
  it("parses routing_table as object", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(typeof res.routing_table).toBe("object")
  })

  it("parses configs as array", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(Array.isArray(res.configs)).toBe(true)
  })

  it("parses available_models correctly", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(res.available_models[0].name).toBe("llama3")
    expect(res.available_models[0].provider).toBe("ollama")
  })

  it("routing entry has all required fields", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    const e = res.routing_table.chat
    expect(typeof e.provider_type).toBe("string")
    expect(typeof e.model_name).toBe("string")
    expect(typeof e.privacy_level).toBe("string")
    expect(typeof e.estimated_cost).toBe("string")
  })
})

// ===== Hook Tests =====

describe("useModels hook", () => {
  it("returns data on success", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const { result } = renderHook(() => useModels(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.available_models[0].name).toBe("llama3")
  })

  it("handles loading state", () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useModels(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("handles error state", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useModels(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("useProviders hook", () => {
  it("returns providers on success", async () => {
    mockGet.mockResolvedValue({
      data: { success: true, providers: [
        { type: "ollama", description: "O" },
        { type: "llama_cpp", description: "L" },
      ]},
    })
    const { result } = renderHook(() => useProviders(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.providers).toHaveLength(2)
  })

  it("handles error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    const { result } = renderHook(() => useProviders(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

// ===== Type Validation =====

describe("Models Type Validation", () => {
  it("ModelsListResponse has routing_table", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(Object.keys(res.routing_table).length).toBeGreaterThan(0)
  })

  it("config has required fields", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(typeof res.configs[0].provider_type).toBe("string")
    expect(typeof res.configs[0].enabled).toBe("boolean")
    expect(typeof res.configs[0].api_key_set).toBe("boolean")
  })

  it("available_model has task_categories array", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(Array.isArray(res.available_models[0].task_categories)).toBe(true)
  })

  it("routing_entry provider_type is valid", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    const validProviders = ["ollama", "llama_cpp", "openai_compatible"]
    for (const [, v] of Object.entries(res.routing_table)) {
      expect(validProviders).toContain(v.provider_type)
    }
  })

  it("routing_entry privacy_level is valid", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    const validPrivacies = ["low", "medium", "high", "strict"]
    for (const [, v] of Object.entries(res.routing_table)) {
      expect(validPrivacies).toContain(v.privacy_level)
    }
  })

  it("test response has connected boolean", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, provider_type: "ollama", connected: true, message: "OK" },
    })
    const res = await testModel("ollama")
    expect(typeof res.connected).toBe("boolean")
  })

  it("generate response has routing and response", async () => {
    mockPost.mockResolvedValue({
      data: {
        success: true,
        routing: entry,
        response: { text: "ok", model: "llama3", usage: {}, error: "" },
      },
    })
    const res = await generateWithModel({ task_category: "chat", prompt: "Hi" })
    expect(typeof res.routing.model_name).toBe("string")
    expect(typeof res.response.text).toBe("string")
  })
})

// ===== Additional Tests =====

describe("Models Additional", () => {
  it("fetchModels with empty routing table", async () => {
    mockGet.mockResolvedValue({
      data: { ...baseResponse, routing_table: {}, available_models: [], configs: [] },
    })
    const res = await fetchModels()
    expect(Object.keys(res.routing_table)).toHaveLength(0)
  })

  it("configs can be empty", async () => {
    mockGet.mockResolvedValue({ data: { ...baseResponse, configs: [] } })
    const res = await fetchModels()
    expect(res.configs).toHaveLength(0)
  })

  it("available_models can be empty", async () => {
    mockGet.mockResolvedValue({ data: { ...baseResponse, available_models: [] } })
    const res = await fetchModels()
    expect(res.available_models).toHaveLength(0)
  })

  it("configureModel with all fields", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    await configureModel({
      provider_type: "openai_compatible",
      endpoint: "http://api.test",
      api_key: "sk-test123",
      priority: 2,
    })
    expect(mockPost).toHaveBeenCalledWith("/models/configure", {
      provider_type: "openai_compatible",
      endpoint: "http://api.test",
      api_key: "sk-test123",
      priority: 2,
    })
  })

  it("configureModel with minimal fields", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    await configureModel({ provider_type: "ollama" })
    expect(mockPost).toHaveBeenCalledWith("/models/configure", { provider_type: "ollama" })
  })

  it("testModel ollama returns connected", async () => {
    mockPost.mockResolvedValue({ data: { success: true, provider_type: "ollama", connected: true, message: "OK" } })
    const res = await testModel("ollama")
    expect(res.message).toBe("OK")
  })

  it("generateWithModel returns model name in response", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, routing: entry, response: { text: "Hi", model: "codellama", usage: { tokens: 5 }, error: "" } },
    })
    const res = await generateWithModel({ task_category: "coding", prompt: "Code" })
    expect(res.response.model).toBe("codellama")
  })

  it("generateWithModel handles error in response", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, routing: entry, response: { text: "", model: "", usage: {}, error: "Timeout" } },
    })
    const res = await generateWithModel({ task_category: "chat", prompt: "Hi" })
    expect(res.response.error).toBe("Timeout")
  })

  it("fetchModels routing_table has chat category", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(res.routing_table.chat).toBeDefined()
  })

  it("fetchModels routing_table has coding category", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(res.routing_table.coding).toBeDefined()
    expect(res.routing_table.coding.model_name).toBe("codellama")
  })

  it("config api_key_set reflects actual key presence", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    expect(res.configs[0].api_key_set).toBe(false)
  })

  it("config provider_type is valid enum", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    for (const c of res.configs) {
      expect(["ollama", "llama_cpp", "openai_compatible"]).toContain(c.provider_type)
    }
  })

  it("available_model task_categories is non-empty when populated", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    for (const m of res.available_models) {
      expect(m.task_categories.length).toBeGreaterThanOrEqual(1)
    }
  })

  it("available_model estimated_cost is string", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    for (const m of res.available_models) {
      expect(typeof m.estimated_cost).toBe("string")
    }
  })

  it("routing_table entry reason is non-empty", async () => {
    mockGet.mockResolvedValue({ data: baseResponse })
    const res = await fetchModels()
    for (const [, v] of Object.entries(res.routing_table)) {
      expect(v.reason.length).toBeGreaterThan(0)
    }
  })

  it("providers list has unique types", async () => {
    mockGet.mockResolvedValue({
      data: {
        success: true,
        providers: [
          { type: "ollama", description: "O" },
          { type: "llama_cpp", description: "L" },
          { type: "openai_compatible", description: "OAI" },
        ],
      },
    })
    const res = await fetchProviders()
    const types = res.providers.map((p) => p.type)
    expect(new Set(types).size).toBe(types.length)
  })

  it("testModel nonexistent provider still returns response", async () => {
    mockPost.mockResolvedValue({
      data: { success: true, provider_type: "unknown", connected: false, message: "Not configured" },
    })
    const res = await testModel("unknown")
    expect(res.connected).toBe(false)
  })
})
