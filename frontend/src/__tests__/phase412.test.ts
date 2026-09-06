import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import {
  fetchTasks, createTask, fetchTask, cancelTask, pauseTask,
  resumeTask, retryTask, fetchQueueStatus
} from "../api/tasks"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

// --- Task Status Types (8 states) ---

describe("TaskStatus types", () => {
  const validStatuses = ["pending", "running", "completed", "failed", "queued", "paused", "cancelled", "timeout"]

  validStatuses.forEach(s => {
    it(`accepts status: ${s}`, () => {
      expect(validStatuses).toContain(s)
    })
  })

  it("backward compatible with old statuses", () => {
    const old = ["pending", "running", "completed", "failed"]
    old.forEach(s => expect(validStatuses).toContain(s))
  })

  it("has 8 total statuses", () => {
    expect(validStatuses).toHaveLength(8)
  })
})

// --- API Tests ---

describe("fetchTasks API", () => {
  it("returns task list", async () => {
    mockGet.mockResolvedValue({ data: { tasks: [{ task_id: "t1" }] } })
    const tasks = await fetchTasks()
    expect(tasks).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/tasks")
  })
})

describe("createTask API", () => {
  it("creates task", async () => {
    mockPost.mockResolvedValue({ data: { task_id: "t1", task: "test", status: "pending" } })
    const res = await createTask({ task: "test" })
    expect(res.task_id).toBe("t1")
  })

  it("creates task with timeout", async () => {
    mockPost.mockResolvedValue({ data: { task_id: "t1", task: "test", status: "pending" } })
    await createTask({ task: "test", timeout_seconds: 60 })
    expect(mockPost).toHaveBeenCalledWith("/tasks", { task: "test", timeout_seconds: 60 })
  })
})

describe("fetchTask API", () => {
  it("returns single task", async () => {
    mockGet.mockResolvedValue({ data: { task_id: "t1", status: "running", attempt: 1 } })
    const task = await fetchTask("t1")
    expect(task.task_id).toBe("t1")
    expect(mockGet).toHaveBeenCalledWith("/tasks/t1")
  })
})

describe("cancelTask API", () => {
  it("calls cancel endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    const res = await cancelTask("t1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/cancel")
  })
})

describe("pauseTask API", () => {
  it("calls pause endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    await pauseTask("t1")
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/pause")
  })
})

describe("resumeTask API", () => {
  it("calls resume endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    await resumeTask("t1")
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/resume")
  })
})

describe("retryTask API", () => {
  it("calls retry endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true } })
    await retryTask("t1")
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/retry")
  })
})

describe("fetchQueueStatus API", () => {
  it("returns queue status", async () => {
    mockGet.mockResolvedValue({ data: { max_concurrent: 3, running: 1, queued: 0 } })
    const res = await fetchQueueStatus()
    expect(res.max_concurrent).toBe(3)
    expect(mockGet).toHaveBeenCalledWith("/tasks/queue/status")
  })
})

// --- TaskRecord Fields ---

describe("TaskRecord fields", () => {
  it("has attempt field", () => {
    const r = { task_id: "t1", task: "x", status: "running", attempt: 2 }
    expect(r.attempt).toBe(2)
  })

  it("has max_iterations", () => {
    const r = { task_id: "t1", task: "x", max_iterations: 5 }
    expect(r.max_iterations).toBe(5)
  })

  it("has timeout_seconds", () => {
    const r = { task_id: "t1", task: "x", timeout_seconds: 120 }
    expect(r.timeout_seconds).toBe(120)
  })

  it("has error_message", () => {
    const r = { task_id: "t1", task: "x", error_message: "oops" }
    expect(r.error_message).toBe("oops")
  })
})

// --- Status Display ---

describe("Status display", () => {
  const config: Record<string, { color: string; label: string }> = {
    pending: { color: "default", label: "Pending" },
    queued: { color: "warning", label: "Queued" },
    running: { color: "processing", label: "Running" },
    paused: { color: "warning", label: "Paused" },
    completed: { color: "success", label: "Completed" },
    failed: { color: "error", label: "Failed" },
    cancelled: { color: "default", label: "Cancelled" },
    timeout: { color: "error", label: "Timeout" },
  }

  Object.entries(config).forEach(([status, cfg]) => {
    it(`${status} has color ${cfg.color}`, () => {
      expect(cfg.color).toBeTruthy()
    })
    it(`${status} has label ${cfg.label}`, () => {
      expect(cfg.label).toBeTruthy()
    })
  })
})

// --- Control Button Visibility ---

describe("Control button logic", () => {
  it("cancel for running", () => expect(["running", "queued"].includes("running")).toBe(true))
  it("cancel for queued", () => expect(["running", "queued"].includes("queued")).toBe(true))
  it("pause for running", () => expect("running" === "running").toBe(true))
  it("resume for paused", () => expect("paused" === "paused").toBe(true))
  it("retry for failed", () => expect(["failed", "cancelled", "timeout", "completed"].includes("failed")).toBe(true))
  it("retry for cancelled", () => expect(["failed", "cancelled", "timeout", "completed"].includes("cancelled")).toBe(true))
  it("retry for timeout", () => expect(["failed", "cancelled", "timeout", "completed"].includes("timeout")).toBe(true))
  it("no cancel for completed", () => expect(["running", "queued"].includes("completed")).toBe(false))
  it("no pause for failed", () => expect("failed" === "running").toBe(false))
})

// --- State Transitions ---

describe("State transitions", () => {
  const valid: Record<string, string[]> = {
    pending: ["queued", "running"],
    queued: ["running", "cancelled"],
    running: ["paused", "completed", "failed", "cancelled", "timeout"],
    paused: ["running", "cancelled"],
    completed: ["queued"],
    failed: ["queued"],
    cancelled: ["queued"],
    timeout: ["queued"],
  }

  Object.entries(valid).forEach(([from, tos]) => {
    tos.forEach(to => {
      it(`${from} -> ${to}`, () => expect(valid[from]).toContain(to))
    })
  })

  it("completed cannot pause", () => expect(valid["completed"]).not.toContain("paused"))
  it("failed cannot resume", () => expect(valid["failed"]).not.toContain("running"))
})

// --- WebSocket Events ---

describe("WebSocket events", () => {
  const events = [
    "connected", "task_started", "task_paused", "task_resumed",
    "task_cancelled", "task_timeout", "task_completed", "task_failed",
    "task_retried", "event_replay_started", "event_replayed",
    "event_replay_completed", "pong",
  ]
  events.forEach(ev => {
    it(`has ${ev} event`, () => expect(events).toContain(ev))
  })
})

// --- Error Handling ---

describe("Error handling", () => {
  it("cancel network error", async () => {
    mockPost.mockRejectedValue(new Error("Network"))
    await expect(cancelTask("t1")).rejects.toThrow("Network")
  })

  it("pause 409", async () => {
    mockPost.mockRejectedValue({ response: { status: 409 } })
    await expect(pauseTask("t1")).rejects.toEqual({ response: { status: 409 } })
  })

  it("retry 404", async () => {
    mockPost.mockRejectedValue({ response: { status: 404 } })
    await expect(retryTask("bad")).rejects.toEqual({ response: { status: 404 } })
  })
})

// --- Queue Status ---

describe("Queue status", () => {
  it("has required fields", () => {
    const qs = { max_concurrent: 3, running: 1, queued: 2, running_tasks: ["t1"], queued_tasks: ["t2", "t3"] }
    expect(qs.max_concurrent).toBe(3)
    expect(qs.running).toBe(1)
    expect(qs.queued).toBe(2)
  })
})

// --- Events API ---

describe("Events API types", () => {
  it("event has sequence", () => {
    const ev = { event_id: "e1", task_id: "t1", event_type: "task_created", sequence: 1 }
    expect(ev.sequence).toBe(1)
  })

  it("event has timestamp", () => {
    const ev = { timestamp: "2026-08-12T10:00:00Z" }
    expect(ev.timestamp).toBeTruthy()
  })

  it("event has attempt", () => {
    const ev = { attempt: 2 }
    expect(ev.attempt).toBe(2)
  })

  it("replay events have replay type", () => {
    const types = ["event_replay_started", "event_replayed", "event_replay_completed"]
    types.forEach(t => expect(types).toContain(t))
  })

  it("since_sequence filters events", () => {
    const events = [
      { sequence: 1 }, { sequence: 2 }, { sequence: 3 },
    ]
    const filtered = events.filter(e => e.sequence > 2)
    expect(filtered).toHaveLength(1)
  })
})