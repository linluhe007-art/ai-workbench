import { Card, Table, Tag, Typography, Space, Empty } from 'antd'
import { BugOutlined } from '@ant-design/icons'
import type { TraceEvent } from '../../types'

const { Text } = Typography

interface TracePanelProps {
  events: TraceEvent[]
  loading?: boolean
}

const eventTypeColor = (t: string) => {
  switch (t) {
    case 'start': return 'processing'
    case 'end': return 'success'
    case 'error': return 'error'
    case 'metric': return 'warning'
    default: return 'default'
  }
}

const columns = [
  {
    title: '时间',
    dataIndex: 'timestamp',
    key: 'timestamp',
    width: 180,
    render: (t: string) => new Date(t).toLocaleString('zh-CN'),
  },
  {
    title: '组件',
    dataIndex: 'component',
    key: 'component',
    width: 100,
    render: (c: string) => <Tag>{c}</Tag>,
  },
  {
    title: '事件',
    dataIndex: 'event_type',
    key: 'event_type',
    width: 100,
    render: (t: string) => <Tag color={eventTypeColor(t)}>{t}</Tag>,
  },
  {
    title: '耗时',
    dataIndex: 'duration_ms',
    key: 'duration_ms',
    width: 80,
    render: (ms: number) => ms > 0 ? `${ms}ms` : '-',
  },
  {
    title: '详情',
    dataIndex: 'metadata',
    key: 'metadata',
    render: (m: Record<string, unknown>) => {
      if (!m || Object.keys(m).length === 0) return '-'
      return (
        <Space size={4} wrap>
          {Object.entries(m).map(([k, v]) => (
            <Tag key={k} style={{ fontSize: 11 }}>
              {k}: {String(v)}
            </Tag>
          ))}
        </Space>
      )
    },
  },
]

export default function TracePanel({ events, loading }: TracePanelProps) {
  if (!events || events.length === 0) {
    return <Empty description="暂无 Trace 数据" />
  }

  return (
    <Card
      title={
        <Space>
          <BugOutlined />
          <span>Trace 事件</span>
          <Tag>{events.length}</Tag>
        </Space>
      }
      size="small"
    >
      <Table
        dataSource={events}
        columns={columns}
        rowKey={(r, i) => `${r.trace_id}-${i}`}
        size="small"
        pagination={{ pageSize: 20 }}
        loading={loading}
      />
    </Card>
  )
}