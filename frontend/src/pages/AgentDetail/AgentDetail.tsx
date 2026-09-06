import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Button, Space, Spin, Row, Col, Descriptions, Tag, Statistic } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, RobotOutlined, ThunderboltOutlined, FileSearchOutlined } from '@ant-design/icons'
import { useAgentCapabilities, useAgentHealth, useAgentHistory } from '../../hooks/useAgentManagement'
import { useAgents } from '../../hooks/useAgents'
import CapabilityPanel from './CapabilityPanel'
import HealthPanel from './HealthPanel'
import AgentHistory from './AgentHistory'

const { Title, Text } = Typography

const agentStateColors: Record<string, string> = {
  idle: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

export default function AgentDetail() {
  const { agent_id } = useParams<{ agent_id: string }>()
  const navigate = useNavigate()

  const { data: agentsData, isLoading: agentsLoading } = useAgents()
  const { data: caps, isLoading: capsLoading, refetch: refetchCaps } = useAgentCapabilities(agent_id || null)
  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useAgentHealth(agent_id || null)
  const { data: history, isLoading: historyLoading, refetch: refetchHistory } = useAgentHistory(agent_id || null)

  const agentInfo = agentsData?.agents?.find((a) => a.id === agent_id)

  const handleRefresh = () => {
    refetchCaps()
    refetchHealth()
    refetchHistory()
  }

  if (agentsLoading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  if (!agentInfo) {
    return (
      <Card>
        <Text>Agent 不存在: {agent_id}</Text>
        <Button onClick={() => navigate('/dashboard')} style={{ marginLeft: 16 }}>返回</Button>
      </Card>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回</Button>
          <Title level={3} style={{ marginBottom: 0 }}>
            <RobotOutlined style={{ marginRight: 8 }} />
            Agent 详情
          </Title>
        </Space>
        <Space>
          <Button icon={<FileSearchOutlined />} onClick={() => navigate(`/artifacts?agent_id=${agent_id}`)}>查看产物</Button>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>刷新</Button>
        </Space>
      </div>

      {/* Basic Info */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }}>
          <Descriptions.Item label="Agent ID">
            <Text code>{agent_id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            <Tag>{agentInfo.type || 'custom'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={agentStateColors[agentInfo.state] || 'default'}>{agentInfo.state}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="健康">
            <Tag color={health?.healthy ? 'success' : health ? 'error' : 'default'}>
              {health?.healthy ? '健康' : health ? '异常' : '检测中...'}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Content */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <CapabilityPanel
              capabilities={caps?.capabilities || []}
              experience={caps?.experience}
            />
            <HealthPanel health={health} loading={healthLoading} />
          </div>
        </Col>
        <Col xs={24} lg={16}>
          <AgentHistory records={history?.records || []} loading={historyLoading} />
        </Col>
      </Row>
    </div>
  )
}
