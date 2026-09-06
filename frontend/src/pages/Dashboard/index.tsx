import { Card, Col, Row, Statistic, Typography, Table, Tag, Spin, Space, Button, Input, message } from 'antd'
import {
  ProjectOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SendOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTasks, useCreateTask } from '../../hooks/useTasks'
import { useAgents, useMetrics } from '../../hooks/useAgents'
import type { TaskRecord, AgentInfo } from '../../types'

const { Title, Paragraph } = Typography

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

const agentStateColors: Record<string, string> = {
  idle: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

export default function Dashboard() {
  const [newTask, setNewTask] = useState('')
  const navigate = useNavigate()
  const { data: tasks, isLoading: tasksLoading, refetch: refetchTasks } = useTasks()
  const { data: agentsData, isLoading: agentsLoading } = useAgents()
  const { data: metrics, isLoading: metricsLoading } = useMetrics()
  const createTask = useCreateTask()

  const handleCreateTask = async () => {
    if (!newTask.trim()) return
    try {
      await createTask.mutateAsync({ task: newTask.trim() })
      message.success('任务已创建')
      setNewTask('')
    } catch {
      message.error('创建失败')
    }
  }

  const taskColumns = [
    { title: '任务 ID', dataIndex: 'task_id', key: 'task_id', ellipsis: true, width: 160, render: (id: string) => <a onClick={() => navigate(`/tasks/${id}`)}>{id}</a> },
    { title: '任务描述', dataIndex: 'task', key: 'task', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '迭代', dataIndex: 'iterations', key: 'iterations', width: 80,
      render: (n: number | undefined) => n ?? '-',
    },
    {
      title: '评分', key: 'score', width: 80,
      render: (_: unknown, r: TaskRecord) => r.evaluation?.score?.toFixed(1) ?? '-',
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
  ]

  const agentColumns = [
    { title: 'Agent ID', dataIndex: 'id', key: 'id', width: 140, render: (id: string) => <a onClick={() => navigate(`/agents/${id}`)}>{id}</a> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 120 },
    {
      title: '状态', dataIndex: 'state', key: 'state', width: 100,
      render: (s: string) => <Tag color={agentStateColors[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '能力', key: 'caps',
      render: (_: unknown, r: AgentInfo) => (
        <Space size={2} wrap>
          {(r.capabilities || []).map((c) => <Tag key={c}>{c}</Tag>)}
        </Space>
      ),
    },
  ]

  const totalTasks = tasks?.length ?? 0
  const completedTasks = tasks?.filter((t) => t.status === 'completed').length ?? 0
  const failedTasks = tasks?.filter((t) => t.status === 'failed').length ?? 0
  const totalAgents = agentsData?.total ?? 0

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>运行工作台</Title>
          <Paragraph type="secondary">AI Agent 运行时控制台 - Phase 4.2</Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} onClick={() => refetchTasks()}>刷新</Button>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="总任务" value={totalTasks} prefix={<ProjectOutlined />} loading={tasksLoading} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="已完成" value={completedTasks} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} loading={tasksLoading} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Agent 数量" value={totalAgents} prefix={<RobotOutlined />} loading={agentsLoading} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="成功率"
              value={metrics ? (metrics.success_rate * 100).toFixed(0) : 0}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              loading={metricsLoading}
            />
          </Card>
        </Col>
      </Row>

      {/* Metrics Detail */}
      {metrics && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="Agent 执行次数" value={metrics.agent_runs} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="Agent 成功率" value={(metrics.agent_success_rate * 100).toFixed(0)} suffix="%" />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="平均耗时" value={metrics.average_duration_ms.toFixed(0)} suffix="ms" />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card size="small">
              <Statistic title="错误总数" value={metrics.total_errors} prefix={<ExclamationCircleOutlined />} valueStyle={metrics.total_errors > 0 ? { color: '#cf1322' } : undefined} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Create Task */}
      <Card style={{ marginTop: 16 }}>
        <Title level={5}>创建任务</Title>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            placeholder="输入任务描述，例如：研究AI趋势并写报告"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            onPressEnter={handleCreateTask}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleCreateTask} loading={createTask.isPending}>
            提交
          </Button>
        </Space.Compact>
      </Card>

      {/* Tasks Table */}
      <Card style={{ marginTop: 16 }} title="任务列表">
        {tasksLoading ? <Spin /> : (
          <Table
            dataSource={tasks || []}
            columns={taskColumns}
            rowKey="task_id"
            size="small"
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* Agents Table */}
      <Card style={{ marginTop: 16 }} title="Agent 列表">
        {agentsLoading ? <Spin /> : (
          <Table
            dataSource={agentsData?.agents || []}
            columns={agentColumns}
            rowKey="id"
            size="small"
            pagination={false}
          />
        )}
      </Card>
    </div>
  )
}
