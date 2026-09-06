import { Tag, Typography, Space } from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons'

const { Text } = Typography

export interface StepNodeData {
  id: string
  type: string
  description: string
  agent: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  duration?: number
}

const statusConfig: Record<string, { bg: string; border: string; color: string; icon: React.ReactNode }> = {
  pending: { bg: '#f5f5f5', border: '#d9d9d9', color: '#8c8c8c', icon: <ClockCircleOutlined /> },
  running: { bg: '#e6f4ff', border: '#91caff', color: '#1677ff', icon: <PlayCircleOutlined /> },
  success: { bg: '#f6ffed', border: '#b7eb8f', color: '#52c41a', icon: <CheckCircleOutlined /> },
  failed: { bg: '#fff2f0', border: '#ffccc7', color: '#ff4d4f', icon: <CloseCircleOutlined /> },
  skipped: { bg: '#f5f5f5', border: '#d9d9d9', color: '#bfbfbf', icon: <MinusCircleOutlined /> },
}

export default function StepNode({ data }: { data: StepNodeData }) {
  const cfg = statusConfig[data.status] || statusConfig.pending

  return (
    <div
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        background: cfg.bg,
        border: `2px solid ${cfg.border}`,
        minWidth: 140,
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        {cfg.icon}
        <Text strong style={{ color: cfg.color, fontSize: 13 }}>{data.id}</Text>
      </div>
      <div style={{ fontSize: 11, color: '#595959' }}>{data.description}</div>
      <div style={{ marginTop: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Tag style={{ fontSize: 10, margin: 0 }}>{data.agent}</Tag>
        {data.duration && data.duration > 0 && (
          <Text type="secondary" style={{ fontSize: 10 }}>{data.duration}ms</Text>
        )}
      </div>
    </div>
  )
}