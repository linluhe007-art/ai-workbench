import { Table, Tag, Typography, Space, Empty, Card } from 'antd'
import { HistoryOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import type { AgentHistoryRecord } from '../../api/agentManagement'

const { Text } = Typography

interface AgentHistoryProps {
  records: AgentHistoryRecord[]
  loading?: boolean
}

const columns = [
  {
    title: '任务',
    dataIndex: 'task_id',
    key: 'task_id',
    ellipsis: true,
  },
  {
    title: '结果',
    dataIndex: 'success',
    key: 'success',
    width: 80,
    render: (s: boolean) =>
      s ? (
        <Tag color="success" icon={<CheckCircleOutlined />}>成功</Tag>
      ) : (
        <Tag color="error" icon={<CloseCircleOutlined />}>失败</Tag>
      ),
  },
  {
    title: '耗时',
    dataIndex: 'duration',
    key: 'duration',
    width: 100,
    render: (ms: number) => (ms > 0 ? `${ms}ms` : '-'),
  },
  {
    title: '时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
    render: (t: string) => (t ? new Date(t).toLocaleString('zh-CN') : '-'),
  },
]

export default function AgentHistory({ records, loading }: AgentHistoryProps) {
  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>执行历史</span>
          {records.length > 0 && <Tag>{records.length}</Tag>}
        </Space>
      }
      size="small"
    >
      {records.length === 0 ? (
        <Empty description="暂无执行记录" />
      ) : (
        <Table
          dataSource={records}
          columns={columns}
          rowKey={(_, i) => String(i)}
          size="small"
          pagination={{ pageSize: 10 }}
          loading={loading}
        />
      )}
    </Card>
  )
}