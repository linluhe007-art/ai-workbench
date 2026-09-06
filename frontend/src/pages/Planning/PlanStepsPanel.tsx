import { Card, Table, Tag, Space, Typography, Empty } from 'antd'
import { OrderedListOutlined } from '@ant-design/icons'

const { Text } = Typography

interface StepInfo {
  id: string
  type: string
  description: string
  depends_on: string[]
  agent_hint: string
}

interface PlanStepsPanelProps {
  steps: StepInfo[] | null
}

const typeColors: Record<string, string> = {
  research: 'blue',
  analysis: 'green',
  writing: 'purple',
  image: 'magenta',
  seo: 'gold',
  custom: 'default',
}

const columns = [
  {
    title: '步骤 ID',
    dataIndex: 'id',
    key: 'id',
    width: 120,
    render: (id: string) => <Text code>{id}</Text>,
  },
  {
    title: '类型',
    dataIndex: 'type',
    key: 'type',
    width: 100,
    render: (t: string) => <Tag color={typeColors[t] || 'default'}>{t}</Tag>,
  },
  {
    title: '描述',
    dataIndex: 'description',
    key: 'description',
    ellipsis: true,
  },
  {
    title: 'Agent',
    dataIndex: 'agent_hint',
    key: 'agent_hint',
    width: 120,
    render: (a: string) => a ? <Tag color="blue">{a}</Tag> : <Text type="secondary">-</Text>,
  },
  {
    title: '依赖',
    dataIndex: 'depends_on',
    key: 'depends_on',
    width: 150,
    render: (deps: string[]) =>
      deps.length > 0
        ? deps.map((d) => <Tag key={d}>{d}</Tag>)
        : <Text type="secondary">-</Text>,
  },
]

export default function PlanStepsPanel({ steps }: PlanStepsPanelProps) {
  if (!steps || steps.length === 0) {
    return <Empty description="无步骤数据" />
  }

  return (
    <Card
      title={
        <Space>
          <OrderedListOutlined />
          <span>计划步骤</span>
          <Tag>{steps.length}</Tag>
        </Space>
      }
      size="small"
    >
      <Table
        dataSource={steps}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={false}
      />
    </Card>
  )
}