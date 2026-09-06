import React from 'react'
import { Card, Descriptions, Tag, Spin, Alert, Typography, Space } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined, SyncOutlined } from '@ant-design/icons'
import { useSystemHealth, useSystemInfo, useReadiness } from '../../hooks/useSystem'

const { Title } = Typography

const StatusTag: React.FC<{ status: string }> = ({ status }) => {
  const config: Record<string, { color: string; icon: React.ReactNode }> = {
    healthy: { color: 'green', icon: <CheckCircleOutlined /> },
    running: { color: 'green', icon: <CheckCircleOutlined /> },
    degraded: { color: 'orange', icon: <WarningOutlined /> },
    unavailable: { color: 'red', icon: <CloseCircleOutlined /> },
    error: { color: 'red', icon: <CloseCircleOutlined /> },
  }
  const c = config[status] || { color: 'default', icon: null }
  return <Tag color={c.color} icon={c.icon}>{status.toUpperCase()}</Tag>
}

const SystemStatus: React.FC = () => {
  const { data: health, isLoading: healthLoading, error: healthError } = useSystemHealth()
  const { data: info, isLoading: infoLoading } = useSystemInfo()
  const { data: readiness, isLoading: readinessLoading } = useReadiness()

  if (healthLoading || infoLoading || readinessLoading) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>正在加载系统状态...</p>
      </div>
    )
  }

  if (healthError) {
    return <Alert type="error" message="加载系统状态失败" description={String(healthError)} />
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>系统状态</Title>

      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card title="运行时">
          <Descriptions column={2}>
            <Descriptions.Item label="状态">
              <StatusTag status={info?.status || 'unknown'} />
            </Descriptions.Item>
            <Descriptions.Item label="实例 ID">{info?.instance_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="运行时长">{readiness?.uptime_seconds ? `${Math.round(readiness.uptime_seconds)}s` : '-'}</Descriptions.Item>
            <Descriptions.Item label="活动任务">{info?.active_tasks ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="启动时间">{info?.started_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="健康状态"><StatusTag status={health?.status || 'unknown'} /></Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="基础设施">
          <Descriptions column={2}>
            <Descriptions.Item label="PostgreSQL">
              <StatusTag status={readiness?.persistence || 'unknown'} />
            </Descriptions.Item>
            <Descriptions.Item label="Redis">
              <StatusTag status={readiness?.redis || 'unknown'} />
            </Descriptions.Item>
            <Descriptions.Item label="持久化">{info?.health?.persistence_status || readiness?.persistence || '-'}</Descriptions.Item>
            <Descriptions.Item label="就绪状态">{readiness?.ready ? <Tag color="green">就绪</Tag> : <Tag color="red">未就绪</Tag>}</Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="队列">
          <Descriptions column={3}>
            <Descriptions.Item label="运行中">{info?.active_tasks ?? 0}</Descriptions.Item>
            <Descriptions.Item label="排队中">{info?.queued_tasks ?? 0}</Descriptions.Item>
            <Descriptions.Item label="最大并发">{info?.health?.max_concurrent ?? 3}</Descriptions.Item>
          </Descriptions>
        </Card>

        {info?.metrics && (
          <Card title="指标">
            <Descriptions column={3}>
              <Descriptions.Item label="任务总数">{info.metrics.total_tasks}</Descriptions.Item>
              <Descriptions.Item label="成功率">{info.metrics.success_rate != null ? `${(info.metrics.success_rate * 100).toFixed(1)}%` : '-'}</Descriptions.Item>
              <Descriptions.Item label="平均耗时">{info.metrics.average_duration ? `${info.metrics.average_duration.toFixed(1)}ms` : '-'}</Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Space>
    </div>
  )
}

export default SystemStatus
