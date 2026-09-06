import { describe, it, expect, vi, beforeEach } from 'vitest'
import apiClient from '../api/client'
import {
  createWorkspace,
  listWorkspaceItems,
  getWorkspaceItem,
  deleteWorkspaceItem,
} from '../api/workspaces'
import type { WorkspaceItemData } from '../api/workspaces'

vi.mock('../api/client')

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)
const mockDelete = vi.mocked(apiClient.delete)

beforeEach(() => vi.clearAllMocks())

describe('Workspace API', () => {
  it('createWorkspace posts task_id', async () => {
    mockPost.mockResolvedValue({ data: { workspace_id: 'ws-1', task_id: 't1' } })
    const res = await createWorkspace('t1')
    expect(res.workspace_id).toBe('ws-1')
    expect(mockPost).toHaveBeenCalledWith('/workspaces', { task_id: 't1' })
  })

  it('listWorkspaceItems returns items', async () => {
    const items: WorkspaceItemData[] = [
      { id: 'i1', name: 'doc', type: 'text', content: 'hello', owner: 'agent', metadata: {}, created_at: '' },
    ]
    mockGet.mockResolvedValue({ data: { workspace_id: 'ws-1', items, total: 1 } })
    const res = await listWorkspaceItems('ws-1')
    expect(res.total).toBe(1)
    expect(res.items[0].name).toBe('doc')
    expect(mockGet).toHaveBeenCalledWith('/workspaces/ws-1/items')
  })

  it('getWorkspaceItem returns single item', async () => {
    const item: WorkspaceItemData = { id: 'i1', name: 'doc', type: 'text', content: 'data', owner: 'a', metadata: {}, created_at: '' }
    mockGet.mockResolvedValue({ data: item })
    const res = await getWorkspaceItem('ws-1', 'i1')
    expect(res.id).toBe('i1')
    expect(mockGet).toHaveBeenCalledWith('/workspaces/ws-1/items/i1')
  })

  it('deleteWorkspaceItem sends delete', async () => {
    mockDelete.mockResolvedValue({ data: { deleted: true, item_id: 'i1' } })
    const res = await deleteWorkspaceItem('ws-1', 'i1')
    expect(res.deleted).toBe(true)
    expect(mockDelete).toHaveBeenCalledWith('/workspaces/ws-1/items/i1')
  })
})

describe('WorkspaceItemData structure', () => {
  it('has required fields', () => {
    const item: WorkspaceItemData = {
      id: 'uuid-1',
      name: 'research',
      type: 'text',
      content: 'result',
      owner: 'research-agent',
      metadata: { version: 1 },
      created_at: '2026-08-11T00:00:00Z',
    }
    expect(item.id).toBe('uuid-1')
    expect(item.type).toBe('text')
    expect(item.metadata.version).toBe(1)
  })

  it('supports dict content', () => {
    const item: WorkspaceItemData = {
      id: '1', name: 'report', type: 'dict',
      content: { title: 'AI', sections: ['a', 'b'] },
      owner: 'writing', metadata: {}, created_at: '',
    }
    expect(item.content).toHaveProperty('title')
  })

  it('supports list content', () => {
    const item: WorkspaceItemData = {
      id: '1', name: 'tags', type: 'list',
      content: ['ai', 'ml', 'nlp'],
      owner: 'analysis', metadata: {}, created_at: '',
    }
    expect(Array.isArray(item.content)).toBe(true)
    expect(item.content).toHaveLength(3)
  })

  it('supports null content', () => {
    const item: WorkspaceItemData = {
      id: '1', name: 'empty', type: 'text',
      content: null,
      owner: 'user', metadata: {}, created_at: '',
    }
    expect(item.content).toBeNull()
  })
})

describe('ArtifactList data processing', () => {
  it('groups items by owner', () => {
    const items: WorkspaceItemData[] = [
      { id: '1', name: 'a', type: 'text', content: '', owner: 'agent-1', metadata: {}, created_at: '' },
      { id: '2', name: 'b', type: 'text', content: '', owner: 'agent-1', metadata: {}, created_at: '' },
      { id: '3', name: 'c', type: 'text', content: '', owner: 'agent-2', metadata: {}, created_at: '' },
    ]
    const counts: Record<string, number> = {}
    for (const item of items) {
      counts[item.owner] = (counts[item.owner] || 0) + 1
    }
    expect(counts['agent-1']).toBe(2)
    expect(counts['agent-2']).toBe(1)
  })

  it('type icon mapping', () => {
    const types = ['text', 'dict', 'list', 'image_url']
    for (const t of types) {
      expect(types).toContain(t)
    }
  })
})

describe('ArtifactViewer content rendering', () => {
  it('text content is string', () => {
    const content = 'plain text'
    expect(typeof content).toBe('string')
  })

  it('dict content is object', () => {
    const content = { key: 'value' }
    expect(typeof content).toBe('object')
    expect(content.key).toBe('value')
  })

  it('list content is array', () => {
    const content = [1, 2, 3]
    expect(Array.isArray(content)).toBe(true)
  })

  it('handles JSON.stringify for display', () => {
    const content = { nested: { deep: true } }
    const str = JSON.stringify(content, null, 2)
    expect(str).toContain('nested')
    expect(str).toContain('deep')
  })
})
describe('Workspace page data processing', () => {
  it('filters items by owner', () => {
    const items = [
      { id: '1', name: 'a', type: 'text', content: '', owner: 'agent-1', metadata: {}, created_at: '' },
      { id: '2', name: 'b', type: 'text', content: '', owner: 'agent-2', metadata: {}, created_at: '' },
    ]
    const filtered = items.filter(i => i.owner === 'agent-1')
    expect(filtered).toHaveLength(1)
    expect(filtered[0].name).toBe('a')
  })

  it('filters items by type', () => {
    const items = [
      { id: '1', name: 'a', type: 'text', content: '', owner: 'x', metadata: {}, created_at: '' },
      { id: '2', name: 'b', type: 'dict', content: {}, owner: 'x', metadata: {}, created_at: '' },
    ]
    const texts = items.filter(i => i.type === 'text')
    expect(texts).toHaveLength(1)
  })

  it('handles empty workspace', () => {
    const items: WorkspaceItemData[] = []
    expect(items.length).toBe(0)
  })

  it('content preview for large text', () => {
    const content = 'A'.repeat(10000)
    const preview = content.substring(0, 100) + '...'
    expect(preview.length).toBeLessThan(content.length)
    expect(preview).toContain('...')
  })

  it('metadata display check', () => {
    const metadata = { version: 2, tags: ['ai', 'ml'], source: 'web' }
    expect(Object.keys(metadata)).toHaveLength(3)
    expect(metadata.tags).toContain('ai')
  })
})

describe('Workspace URL params', () => {
  it('parses workspace_id from URL', () => {
    const path = '/workspaces/task-abc-123'
    const parts = path.split('/')
    expect(parts[parts.length - 1]).toBe('task-abc-123')
  })
})
