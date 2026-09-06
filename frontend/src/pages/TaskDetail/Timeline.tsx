import { Timeline as AntTimeline, Tag, Typography, Empty } from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { TraceEvent, WsEvent } from '../../types'

const { Text } = Typography

interface TimelinePanelProps {
  traces: TraceEvent[]
  wsEvents: WsEvent[]
}

const eventIcon = (type: string) => {
  switch (type) {
    case 'start': return <PlayCircleOutlined style={{ color: '#1677ff' }} />
    case 'end': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    case 'error': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    case 'metric': return <ThunderboltOutlined style={{ color: '#faad14' }} />
    case 'task_started': return <PlayCircleOutlined style={{ color: '#1677ff' }} />
    case 'task_completed': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    case 'task_failed': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    case 'agent_started': return <ReloadOutlined spin style={{ color: '#1677ff' }} />
    case 'agent_finished': return <CheckCircleOutlined style={{ color: '#722ed1' }} />
    case 'step_completed': return <CheckCircleOutlined style={{ color: '#13c2c2' }} />
    case 'evaluation_updated': return <ThunderboltOutlined style={{ color: '#faad14' }} />
    default: return <ClockCircleOutlined />
  }
}

const componentColor = (c: string) => {
  switch (c) {
    case 'loop': return 'blue'
    case 'executor': return 'green'
    case 'agent': return 'purple'
    default: return 'default'
  }
}

export default function TimelinePanel({ traces, wsEvents }: TimelinePanelProps) {
  const items = [
    ...traces.map((e) => ({
      key: `trace-${e.trace_id}-${e.timestamp}`,
      dot: eventIcon(e.event_type),
      children: (
        <div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <Tag color={componentColor(e.component)}>{e.component}</Tag>
            <Text strong>{e.event_type}</Text>
            {e.duration_ms > 0 && <Text type="secondary">{e.duration_ms}ms</Text>}
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {new Date(e.timestamp).toLocaleString('zh-CN')}
          </Text>
          {Object.keys(e.metadata).length > 0 && (
            <div style={{ marginTop: 4 }}>
              {Object.entries(e.metadata).map(([k, v]) => (
                <Tag key={k} style={{ fontSize: 11 }}>
                  {k}: {String(v)}
                </Tag>
              ))}
            </div>
          )}
        </div>
      ),
    })),
    ...wsEvents.map((e, i) => ({
      key: `ws-${i}-${e.timestamp}`,
      dot: eventIcon(e.event),
      color: e.event.includes('fail') ? 'red' : e.event.includes('complete') ? 'green' : 'blue',
      children: (
        <div>
          <Text strong>{e.event}</Text>
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
            {new Date(e.timestamp).toLocaleString('zh-CN')}
          </Text>
          {Object.keys(e.data).length > 0 && (
            <div style={{ marginTop: 4 }}>
              {Object.entries(e.data).map(([k, v]) => (
                <Tag key={k} style={{ fontSize: 11 }}>
                  {k}: {String(v)}
                </Tag>
              ))}
            </div>
          )}
        </div>
      ),
    })),
  ]

  // Sort by timestamp (traces first, then ws events appended)
  if (items.length === 0) {
    return <Empty description="暂无执行记录" />
  }

  return <AntTimeline items={items} mode="left" />
}