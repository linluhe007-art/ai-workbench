import type { WsEvent } from '../types'

type EventHandler = (event: WsEvent) => void

export class TaskWsClient {
  private taskId: string
  private ws: WebSocket | null = null
  private handlers: Map<string, EventHandler[]> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  constructor(taskId: string) {
    this.taskId = taskId
  }

  connect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/v1/ws/tasks/${this.taskId}`
    this.ws = new WebSocket(url)
    this.ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data)
        this.dispatch(event.event, event)
      } catch { /* ignore */ }
    }
    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 5000)
    }
    this.ws.onerror = () => { this.ws?.close() }
  }

  on(eventType: string, handler: EventHandler): void {
    const list = this.handlers.get(eventType) || []
    list.push(handler)
    this.handlers.set(eventType, list)
  }

  off(eventType: string, handler: EventHandler): void {
    const list = this.handlers.get(eventType)
    if (list) this.handlers.set(eventType, list.filter((h) => h !== handler))
  }

  ping(): void { this.ws?.send('ping') }

  close(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  private dispatch(eventType: string, event: WsEvent): void {
    for (const h of this.handlers.get(eventType) || []) h(event)
    for (const h of this.handlers.get('*') || []) h(event)
  }
}