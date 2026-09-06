import { Card, Table, Tag, Typography, Empty, Space } from 'antd'
import { TeamOutlined } from '@ant-design/icons'

const { Text } = Typography

interface AgentSelectionPanelProps {
  selectedAgents: Record<string, string>
  capabilities: Record<string, string[]>
}

export default function AgentSelectionPanel({ selectedAgents, capabilities }: AgentSelectionPanelProps) {
  const entries = Object.entries(selectedAgents)
  if (entries.length === 0) {
    return <Empty description="无 Agent 选择数据" />
  }

  const data = entries.map(([stepId, agentId]) => ({
    step_id: stepId,
    selected_agent: agentId,
    candidates: capabilities[stepId] || [],
  }))

  const columns = [
    {
      title: '步骤',
      dataIndex: 'step_id',
      key: 'step_id',
      width: 120,
      render: (id: string) => <Text code>{id}</Text>,
    },
    {
      title: '选中 Agent',
      dataIndex: 'selected_agent',
      key: 'selected_agent',
      width: 150,
      render: (a: string) => <Tag color="blue">{a}</Tag>,
    },
    {
      title: '候选 Agents',
      dataIndex: 'candidates',
      key: 'candidates',
      render: (candidates: string[]) => (
        <Space size={4} wrap>
          {candidates.length > 0
            ? candidates.map((c) => <Tag key={c}>{c}</Tag>)
            : <Text type="secondary">-</Text>
          }
        </Space>
      ),
    },
  ]

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>Agent 选择</span>
        </Space>
      }
      size="small"
    >
      <Table dataSource={data} columns={columns} rowKey="step_id" size="small" pagination={false} />
    </Card>
  )
}