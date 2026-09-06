import { Card, Descriptions, Tag, Typography, Space, Empty, Button } from 'antd'
import { CloseOutlined } from '@ant-design/icons'
import type { WorkflowStep } from '../../api/workflows'

const { Text } = Typography

interface StepDetailPanelProps {
  step: WorkflowStep | null
  onClose: () => void
}

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
  skipped: 'warning',
}

const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  success: '成功',
  failed: '失败',
  skipped: '已跳过',
}

export default function StepDetailPanel({ step, onClose }: StepDetailPanelProps) {
  if (!step) {
    return <Empty description="点击节点查看详情" />
  }

  return (
    <Card
      title={
        <Space>
          <span>Step: {step.id}</span>
          <Tag color={statusColors[step.status]}>{statusLabels[step.status]}</Tag>
        </Space>
      }
      extra={<Button icon={<CloseOutlined />} size="small" onClick={onClose} />}
      size="small"
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="类型">
          <Tag>{step.type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="描述">{step.description}</Descriptions.Item>
        <Descriptions.Item label="Agent">
          <Tag color="blue">{step.agent}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="依赖">
          {step.depends_on.length > 0
            ? step.depends_on.map((d) => <Tag key={d}>{d}</Tag>)
            : <Text type="secondary">无</Text>
          }
        </Descriptions.Item>
        <Descriptions.Item label="开始时间">
          {step.started_at ? new Date(step.started_at).toLocaleString('zh-CN') : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="结束时间">
          {step.finished_at ? new Date(step.finished_at).toLocaleString('zh-CN') : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="耗时">
          {step.duration > 0 ? `${step.duration}ms` : '-'}
        </Descriptions.Item>
        {step.error && (
          <Descriptions.Item label="错误">
            <Text type="danger">{step.error}</Text>
          </Descriptions.Item>
        )}
      </Descriptions>
    </Card>
  )
}