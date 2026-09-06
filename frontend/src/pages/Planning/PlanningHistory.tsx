import { Table, Tag, Typography, Space, Card, Empty } from 'antd'
import { HistoryOutlined } from '@ant-design/icons'
import type { PlanningDebugSession } from '../../api/planning'

const { Text } = Typography

interface PlanningHistoryProps {
  sessions: PlanningDebugSession[]
  loading?: boolean
  onSelect: (sessionId: string) => void
}

const plannerColors: Record<string, string> = {
  llm: 'blue',
  rule: 'orange',
}

export default function PlanningHistory({ sessions, loading, onSelect }: PlanningHistoryProps) {
  if (!sessions || sessions.length === 0) {
    return <Empty description="暂无 Planning 记录" />
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t: string) => new Date(t).toLocaleString('zh-CN'),
    },
    {
      title: '任务',
      dataIndex: 'task',
      key: 'task',
      ellipsis: true,
      render: (task: string, record: PlanningDebugSession) => (
        <a onClick={() => onSelect(record.session_id)}>{task}</a>
      ),
    },
    {
      title: '规划器',
      dataIndex: 'planner_type',
      key: 'planner_type',
      width: 100,
      render: (t: string) => <Tag color={plannerColors[t] || 'default'}>{t}</Tag>,
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 100,
      render: (ms: number) => `${ms.toFixed(0)}ms`,
    },
    {
      title: '降级',
      dataIndex: 'fallback_used',
      key: 'fallback_used',
      width: 90,
      render: (f: boolean) => f ? <Tag color="warning">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '状态',
      key: 'status',
      width: 80,
      render: (_: unknown, record: PlanningDebugSession) =>
        record.error ? <Tag color="error">错误</Tag> : <Tag color="success">成功</Tag>,
    },
  ]

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>Planning 历史</span>
          <Tag>{sessions.length}</Tag>
        </Space>
      }
      size="small"
    >
      <Table
        dataSource={sessions}
        columns={columns}
        rowKey="session_id"
        size="small"
        pagination={{ pageSize: 10 }}
        loading={loading}
      />
    </Card>
  )
}