import React from 'react'
import { Card, Col, Row, Statistic, Spin, Alert, Typography, Progress, Table } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useMetrics, useTaskMetrics, useAgentMetrics } from '../../hooks/useMetrics'

const { Title } = Typography

const MetricsDashboard: React.FC = () => {
  const { data: allMetrics, isLoading, error } = useMetrics()
  const { data: taskMetrics } = useTaskMetrics()
  const { data: agentMetrics } = useAgentMetrics()

  if (isLoading) return <div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /><p>正在加载监控数据...</p></div>
  if (error) return <Alert type="error" message="加载监控数据失败" description={String(error)} />

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>系统监控</Title>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card><Statistic title="CPU" value={allMetrics?.cpu?.percent ?? 0} suffix="%" precision={1} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="内存" value={allMetrics?.memory?.percent ?? 0} suffix="%" precision={1} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="进程内存" value={allMetrics?.memory?.process_mb ?? 0} suffix="MB" precision={1} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="运行时长" value={Math.round((allMetrics?.runtime?.uptime_seconds ?? 0) / 60)} suffix="min" /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="任务">
            <Statistic title="总数" value={taskMetrics?.total ?? 0} />
            <Progress percent={Math.round((taskMetrics?.success_rate ?? 0) * 100)} status="active" />
            <p>Completed: {taskMetrics?.completed ?? 0} | Failed: {taskMetrics?.failed ?? 0}</p>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="队列">
            <Statistic title="运行中" value={allMetrics?.queue?.running ?? 0} prefix={<CheckCircleOutlined />} />
            <Statistic title="排队中" value={allMetrics?.queue?.queued ?? 0} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Agent">
            <Statistic title="总执行次数" value={agentMetrics?.total_executions ?? 0} />
            <Statistic title="平均延迟" value={allMetrics?.agents?.latency?.avg?.toFixed(1) ?? 0} suffix="ms" />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default MetricsDashboard
