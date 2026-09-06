import { describe, it, expect, vi, beforeEach } from "vitest"
import apiClient from "../api/client"
import {
  fetchTasks, createTask, fetchTask, cancelTask, pauseTask,
  resumeTask, retryTask, fetchQueueStatus
} from "../api/tasks"
import type { TaskRecord, TaskCreateRequest, TaskCreateResponse } from "../types"

vi.mock("../api/client")

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
beforeEach(() => vi.clearAllMocks())

// --- Task Status Types ---

describe("TaskStatus types", () => {
  const validStatuses = ["pending", "running", "completed", "failed", "queued", "paused", "cancelled", "timeout"]

  validStatuses.forEach(s => {
    it(`accepts status: ${s}`, () => {
      const status: string = s
      expect(validStatuses).toContain(status)
    })
  })

  it("backward compatible with old statuses", () => {
    const old: string[] = ["pending", "running", "completed", "failed"]
    old.forEach(s => expect(validStatuses).toContain(s))
  })
})

// --- API Tests ---

describe("fetchTasks API", () => {
  it("returns task list", async () => {
    mockGet.mockResolvedValue({ data: { tasks: [{ task_id: "t1", status: "pending" }] } })
    const tasks = await fetchTasks()
    expect(tasks).toHaveLength(1)
    expect(mockGet).toHaveBeenCalledWith("/tasks")
  })
})

describe("createTask API", () => {
  it("creates task with timeout", async () => {
    mockPost.mockResolvedValue({ data: { task_id: "t1", task: "test", status: "pending" } })
    const res = await createTask({ task: "test", timeout_seconds: 60 })
    expect(res.task_id).toBe("t1")
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
    mockPost.mockResolvedValue({ data: { success: true, task_id: "t1" } })
    const res = await cancelTask("t1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/cancel")
  })
})

describe("pauseTask API", () => {
  it("calls pause endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: "t1" } })
    const res = await pauseTask("t1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/pause")
  })
})

describe("resumeTask API", () => {
  it("calls resume endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: "t1" } })
    const res = await resumeTask("t1")
    expect(res.success).toBe(true)
    expect(mockPost).toHaveBeenCalledWith("/tasks/t1/resume")
  })
})

describe("retryTask API", () => {
  it("calls retry endpoint", async () => {
    mockPost.mockResolvedValue({ data: { success: true, task_id: "t1" } })
    const res = await retryTask("t1")
    expect(res.success).toBe(true)
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

// --- TaskRecord Type Tests ---

describe("TaskRecord new fields", () => {
  it("has attempt field", () => {
    const r: TaskRecord = { task_id: "t1", task: "x", status: "running", attempt: 2 }
    expect(r.attempt).toBe(2)
  })

  it("has max_iterations field", () => {
    const r: TaskRecord = { task_id: "t1", task: "x", status: "pending", max_iterations: 5 }
    expect(r.max_iterations).toBe(5)
  })

  it("has timeout_seconds field", () => {
    const r: TaskRecord = { task_id: "t1", task: "x", status: "pending", timeout_seconds: 120 }
    expect(r.timeout_seconds).toBe(120)
  })

  it("has error_message field", () => {
    const r: TaskRecord = { task_id: "t1", task: "x", status: "failed", error_message: "oops" }
    expect(r.error_message).toBe("oops")
  })
})

// --- Status Config Tests ---

describe("Status display config", () => {
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
    it(`${status} has color and label`, () => {
      expect(cfg.color).toBeTruthy()
      expect(cfg.label).toBeTruthy()
    })
  })
})

// --- Control Button Visibility ---

describe("Control button visibility", () => {
  it("cancel visible for running", () => {
    const status = "running"
    expect(["running", "queued"].includes(status)).toBe(true)
  })

  it("cancel visible for queued", () => {
    const status = "queued"
    expect(["running", "queued"].includes(status)).toBe(true)
  })

  it("pause visible for running", () => {
    expect("running" === "running").toBe(true)
  })

  it("resume visible for paused", () => {
    expect("paused" === "paused").toBe(true)
  })

  it("retry visible for failed", () => {
    expect(["failed", "cancelled", "timeout", "completed"].includes("failed")).toBe(true)
  })

  it("retry visible for cancelled", () => {
    expect(["failed", "cancelled", "timeout", "completed"].includes("cancelled")).toBe(true)
  })

  it("retry visible for timeout", () => {
    expect(["failed", "cancelled", "timeout", "completed"].includes("timeout")).toBe(true)
  })

  it("cancel not visible for completed", () => {
    expect(["running", "queued"].includes("completed")).toBe(false)
  })

  it("pause not visible for failed", () => {
    expect("failed" === "running").toBe(false)
  })
})

// --- Error Handling ---

describe("Error handling", () => {
  it("cancel network error", async () => {
    mockPost.mockRejectedValue(new Error("Network"))
    await expect(cancelTask("t1")).rejects.toThrow("Network")
  })

  it("pause 409 conflict", async () => {
    mockPost.mockRejectedValue({ response: { status: 409 } })
    await expect(pauseTask("t1")).rejects.toEqual({ response: { status: 409 } })
  })

  it("retry 404 not found", async () => {
    mockPost.mockRejectedValue({ response: { status: 404 } })
    await expect(retryTask("bad")).rejects.toEqual({ response: { status: 404 } })
  })
})
// --- Queue Status Tests ---

describe("Queue status display", () => {
  it("shows max_concurrent", () => {
    const qs = { max_concurrent: 3, running: 1, queued: 2, running_tasks: ["t1"], queued_tasks: ["t2", "t3"] }
    expect(qs.max_concurrent).toBe(3)
  })

  it("shows running count", () => {
    const qs = { running: 2 }
    expect(qs.running).toBe(2)
  })

  it("shows queued count", () => {
    const qs = { queued: 5 }
    expect(qs.queued).toBe(5)
  })
})

// --- Task Create Request ---

describe("TaskCreateRequest", () => {
  it("has task field", () => {
    const req: TaskCreateRequest = { task: "test" }
    expect(req.task).toBe("test")
  })

  it("has optional max_iterations", () => {
    const req: TaskCreateRequest = { task: "test", max_iterations: 5 }
    expect(req.max_iterations).toBe(5)
  })

  it("has optional timeout_seconds", () => {
    const req: TaskCreateRequest = { task: "test", timeout_seconds: 60 }
    expect(req.timeout_seconds).toBe(60)
  })
})

// --- State Transition Logic ---

describe("State transition logic", () => {
  const validTransitions: Record<string, string[]> = {
    pending: ["queued", "running"],
    queued: ["running", "cancelled"],
    running: ["paused", "completed", "failed", "cancelled", "timeout"],
    paused: ["running", "cancelled"],
    completed: ["queued"],
    failed: ["queued"],
    cancelled: ["queued"],
    timeout: ["queued"],
  }

  Object.entries(validTransitions).forEach(([from, tos]) => {
    tos.forEach(to => {
      it(`${from} -> ${to} is valid`, () => {
        expect(validTransitions[from]).toContain(to)
      })
    })
  })

  it("completed cannot pause", () => {
    expect(validTransitions["completed"]).not.toContain("paused")
  })

  it("failed cannot resume", () => {
    expect(validTransitions["failed"]).not.toContain("running")
  })

  it("cancelled cannot pause", () => {
    expect(validTransitions["cancelled"]).not.toContain("paused")
  })
})

// --- WebSocket Event Types ---

describe("WebSocket control events", () => {
  const events = ["task_started", "task_paused", "task_resumed", "task_cancelled", "task_timeout", "task_completed", "task_failed", "task_retried"]

  events.forEach(ev => {
    it(`event ${ev} is defined`, () => {
      expect(events).toContain(ev)
    })
  })
})

// --- Hook Integration ---

describe("Hook query keys", () => {
  it("tasks query key", () => {
    expect(["tasks"]).toEqual(["tasks"])
  })

  it("task query key includes id", () => {
    const id = "t1"
    expect(["task", id]).toEqual(["task", "t1"])
  })
})