import { Card, Tag, Descriptions, Badge, Typography, Space } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  MinusCircleOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import type { AgentHealth } from '../../api/agentManagement'

const { Text } = Typography

interface HealthPanelProps {
  health: AgentHealth | undefined
  loading?: boolean
}

const stateConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  IDLE: { color: 'default', icon: <MinusCircleOutlined />, label: '空闲' },
  READY: { color: 'success', icon: <CheckCircleOutlined />, label: '就绪' },
  RUNNING: { color: 'processing', icon: <SyncOutlined spin />, label: '运行中' },
  COMPLETED: { color: 'success', icon: <CheckCircleOutlined />, label: '已完成' },
  FAILED: { color: 'error', icon: <CloseCircleOutlined />, label: '失败' },
  STOPPED: { color: 'warning', icon: <MinusCircleOutlined />, label: '已停止' },
  UNKNOWN: { color: 'default', icon: <MinusCircleOutlined />, label: '未知' },
}

export default function HealthPanel({ health, loading }: HealthPanelProps) {
  if (!health) {
    return (
      <Card title={<Space><HeartOutlined /><span>健康状态</span></Space>} size="small" loading={loading}>
        <Text type="secondary">无数据</Text>
      </Card>
    )
  }

  const cfg = stateConfig[health.state] || stateConfig.UNKNOWN

  return (
    <Card
      title={
        <Space>
          <HeartOutlined />
          <span>健康状态</span>
          <Badge status={health.healthy ? 'success' : 'error'} text={health.healthy ? '健康' : '异常'} />
        </Space>
      }
      size="small"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="状态">
          <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="原始状态">
          <Text code>{health.state}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="最后心跳">
          {health.last_heartbeat ? new Date(health.last_heartbeat).toLocaleString('zh-CN') : '无'}
        </Descriptions.Item>
        {health.error && (
          <Descriptions.Item label="错误">
            <Text type="danger">{health.error}</Text>
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  )
}