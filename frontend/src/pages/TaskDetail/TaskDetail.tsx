import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Col, Row, Typography, Tag, Descriptions, Spin, Button, Space, Badge, Statistic, Tabs } from 'antd'
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  BranchesOutlined,
  FieldTimeOutlined,
  BugOutlined,
  ContainerOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { useTask } from '../../hooks/useTasks'
import { useTaskTrace } from '../../hooks/useTrace'
import { useWorkflow } from '../../hooks/useWorkflow'
import { TaskWsClient } from '../../websocket/client'
import TimelinePanel from './Timeline'
import EvaluationPanel from './EvaluationPanel'
import TracePanel from './TracePanel'
import WorkflowViewer from '../Workflow/WorkflowViewer'
import ArtifactPanel from './ArtifactPanel'
import ExecutionTracePanel from './ExecutionTracePanel'
import type { WsEvent } from '../../types'

const { Title, Text } = Typography

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, label: '待处理' },
  running: { color: 'processing', icon: <SyncOutlined spin />, label: '运行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, label: '已完成' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, label: '失败' },
}

export default function TaskDetail() {
  const { task_id } = useParams<{ task_id: string }>()
  const navigate = useNavigate()
  const { data: task, isLoading, refetch } = useTask(task_id || null)
  const { data: traceData, refetch: refetchTrace } = useTaskTrace(task_id || null)
  const { data: workflow, isLoading: workflowLoading, refetch: refetchWorkflow } = useWorkflow(task_id || null)

  const [wsEvents, setWsEvents] = useState<WsEvent[]>([])
  const [wsConnected, setWsConnected] = useState(false)

  useEffect(() => {
    if (!task_id) return
    const client = new TaskWsClient(task_id)
    client.on('*', (event: WsEvent) => {
      setWsEvents((prev) => [...prev, event])
      if (['task_completed', 'task_failed', 'step_completed'].includes(event.event)) {
        refetch()
        refetchTrace()
        refetchWorkflow()
      }
    })
    client.on('connected', () => setWsConnected(true))
    client.connect()
    return () => { client.close(); setWsConnected(false) }
  }, [task_id, refetch, refetchTrace, refetchWorkflow])

  const handleRefresh = useCallback(() => {
    refetch()
    refetchTrace()
    refetchWorkflow()
  }, [refetch, refetchTrace, refetchWorkflow])

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  if (!task) {
    return (
      <Card>
        <Text>任务不存在: {task_id}</Text>
        <Button onClick={() => navigate('/dashboard')} style={{ marginLeft: 16 }}>返回</Button>
      </Card>
    )
  }

  const cfg = statusConfig[task.status] || statusConfig.pending

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回</Button>
          <Title level={3} style={{ marginBottom: 0 }}>任务详情</Title>
          <Badge status={wsConnected ? 'success' : 'default'} text={wsConnected ? 'WebSocket已连接' : '未连接'} />
        </Space>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh}>刷新</Button>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }}>
          <Descriptions.Item label="任务 ID"><Text code>{task.task_id}</Text></Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag></Descriptions.Item>
          <Descriptions.Item label="迭代次数">{task.iterations ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="任务描述" span={2}>{task.task}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {task.execution && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="状态" value={task.execution.status} /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="耗时" value={task.execution.duration_ms} suffix="ms" /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="成功步骤" value={task.execution.success_count} valueStyle={{ color: '#3f8600' }} /></Card></Col>
          <Col xs={12} sm={6}><Card size="small"><Statistic title="失败步骤" value={task.execution.failed_count} valueStyle={task.execution.failed_count > 0 ? { color: '#cf1322' } : undefined} /></Card></Col>
        </Row>
      )}

      <Tabs
        defaultActiveKey="timeline"
        items={[
          {
            key: 'timeline',
            label: <span><FieldTimeOutlined /> 时间线</span>,
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={16}>
                  <Card title="执行时间线" size="small">
                    <TimelinePanel traces={traceData?.events || []} wsEvents={wsEvents} />
                  </Card>
                </Col>
                <Col xs={24} lg={8}>
                  <EvaluationPanel
                    score={task.evaluation?.score}
                    quality={task.evaluation?.quality}
                    issues={task.evaluation?.issues}
                  />
                </Col>
              </Row>
            ),
          },
          {
            key: 'execution-trace',
            label: <span><BulbOutlined /> AI决策链</span>,
            children: <ExecutionTracePanel taskId={task_id || null} />,
          },
          {
            key: 'workflow',
            label: <span><BranchesOutlined /> Workflow DAG</span>,
            children: <WorkflowViewer workflow={workflow} loading={workflowLoading} />,
          },
          {
            key: 'artifacts',
            label: <span><ContainerOutlined /> Artifacts</span>,
            children: <ArtifactPanel taskId={task_id || null} />,
          },
          {
            key: 'trace',
            label: <span><BugOutlined /> Trace</span>,
            children: <TracePanel events={traceData?.events || []} />,
          },
        ]}
      />

      {wsEvents.length > 0 && (
        <Card title={WebSocket事件 ()} size="small" style={{ marginTop: 16 }}>
          <div style={{ maxHeight: 200, overflow: 'auto' }}>
            {wsEvents.map((e, i) => (
              <div key={i} style={{ padding: '2px 0', fontSize: 12, fontFamily: 'monospace' }}>
                <Tag color="blue">{e.event}</Tag>
                <Text type="secondary">{new Date(e.timestamp).toLocaleTimeString('zh-CN')}</Text>
                {Object.keys(e.data).length > 0 && (
                  <Text code style={{ marginLeft: 8 }}>{JSON.stringify(e.data)}</Text>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
