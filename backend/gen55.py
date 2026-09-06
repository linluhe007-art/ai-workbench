import os

# Add route to App.tsx
app_path = r"E:\半自动工作台\frontend\src\App.tsx"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

if "import AgentTeam from" not in content:
    content = content.replace(
        "import AgentManagement from './pages/AgentManagement/AgentManagement'",
        "import AgentManagement from './pages/AgentManagement/AgentManagement'\nimport AgentTeam from './pages/AgentTeam'"
    )
if "<Route path=\"agents/team\"" not in content:
    content = content.replace(
        "<Route path=\"agents/manage\" element={<AgentManagement />} />",
        "<Route path=\"agents/manage\" element={<AgentManagement />} />\n        <Route path=\"agents/team\" element={<AgentTeam />} />"
    )

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
print("App.tsx updated")

# Frontend tests
test_path = r"E:\半自动工作台\frontend\src\__tests__\personalAgents.test.ts"
with open(test_path, "w", encoding="utf-8") as f:
    f.write('''import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import React from "react"
import apiClient from "../api/client"
import { fetchPersonalAgents, selectAgent, fetchDelegations, fetchAgentRoles } from "../api/personalAgents"
import { usePersonalAgents, useDelegations, useAgentRoles } from "../hooks/usePersonalAgents"

vi.mock("../api/client")
const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

function wrapper(obj: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return React.createElement(QueryClientProvider, { client: qc }, obj.children)
}

const baseMember = { id: "m1", role: "research", agent_id: "", name: "Research Agent", capabilities: ["research"], total_tasks: 5, success_tasks: 4, success_rate: 0.8, avg_duration_ms: 300, active: true, created_at: "2026-01-01T00:00:00" }
const baseTeamResp = { success: true, members: [baseMember], stats: { total_members: 4, active_members: 4, total_tasks: 0, total_success: 0, overall_success_rate: 0 } }
const baseSelectResp = { success: true, task_type: "research", member: baseMember }

describe("Personal Agents API", () => {
  it("fetchPersonalAgents calls GET", async () => {
    mockGet.mockResolvedValue({ data: baseTeamResp })
    const res = await fetchPersonalAgents()
    expect(res.success).toBe(true)
    expect(res.members).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/agents/personal")
  })

  it("selectAgent calls POST", async () => {
    mockPost.mockResolvedValue({ data: baseSelectResp })
    const res = await selectAgent("research")
    expect(res.success).toBe(true)
    expect(res.member.role).toBe("research")
  })

  it("selectAgent with task description", async () => {
    mockPost.mockResolvedValue({ data: baseSelectResp })
    const res = await selectAgent("", [], "write a report")
    expect(res.success).toBe(true)
  })

  it("fetchDelegations calls GET", async () => {
    mockGet.mockResolvedValue({ data: { success: true, delegations: [], total: 0 } })
    const res = await fetchDelegations()
    expect(res.success).toBe(true)
  })

  it("fetchAgentRoles calls GET", async () => {
    mockGet.mockResolvedValue({ data: { success: true, roles: [] } })
    const res = await fetchAgentRoles()
    expect(res.success).toBe(true)
  })
})

describe("usePersonalAgents hook", () => {
  it("returns team data", async () => {
    mockGet.mockResolvedValue({ data: baseTeamResp })
    const { result } = renderHook(() => usePersonalAgents(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.members[0].role).toBe("research")
  })
})

describe("useDelegations hook", () => {
  it("returns delegations", async () => {
    mockGet.mockResolvedValue({ data: { success: true, delegations: [{ id: "d1", task_id: "t1", role: "research", success: true }], total: 1 } })
    const { result } = renderHook(() => useDelegations(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

describe("useAgentRoles hook", () => {
  it("returns roles", async () => {
    mockGet.mockResolvedValue({ data: { success: true, roles: [{ name: "R", role: "research", capabilities: [], tools: [], description: "desc" }] } })
    const { result } = renderHook(() => useAgentRoles(), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
  })
})

describe("Error handling", () => {
  it("handles fetch error", async () => {
    mockGet.mockRejectedValue(new Error("Fail"))
    await expect(fetchPersonalAgents()).rejects.toThrow("Fail")
  })
  it("handles select error", async () => {
    mockPost.mockRejectedValue(new Error("Fail"))
    await expect(selectAgent("x")).rejects.toThrow("Fail")
  })
})

describe("Edge cases", () => {
  it("handles empty team", async () => {
    mockGet.mockResolvedValue({ data: { success: true, members: [], stats: { total_members: 0, active_members: 0, total_tasks: 0, total_success: 0, overall_success_rate: 0 } } })
    const res = await fetchPersonalAgents()
    expect(res.members).toEqual([])
  })
  it("handles empty task type", async () => {
    mockPost.mockResolvedValue({ data: { success: false, task_type: "", member: null } })
    const res = await selectAgent("")
    expect(res.success).toBe(false)
  })
})
''')

print("Frontend test created")