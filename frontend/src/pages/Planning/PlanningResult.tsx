import { Card, Descriptions, Tag, Space, Divider, Alert, Typography } from 'antd'
import {
  ClockCircleOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { PlanningDebugSession } from '../../api/planning'
import PromptPanel from './PromptPanel'
import RawResponsePanel from './RawResponsePanel'
import PlanStepsPanel from './PlanStepsPanel'
import AgentSelectionPanel from './AgentSelectionPanel'

const { Title } = Typography

interface PlanningResultProps {
  session: PlanningDebugSession
}

const plannerColorMap: Record<string, string> = {
  llm: 'blue',
  rule: 'orange',
}

export default function PlanningResult({ session }: PlanningResultProps) {
  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Summary */}
      <Card size="small">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="会话 ID">
            <Tag>{session.session_id}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="规划器">
            <Tag color={plannerColorMap[session.planner_type] || 'default'}>
              {session.planner_type}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="任务" span={2}>
            {session.task}
          </Descriptions.Item>
          <Descriptions.Item label="耗时">
            <Space size={4}>
              <ClockCircleOutlined />
              {session.duration_ms.toFixed(0)}ms
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="降级">
            {session.fallback_used ? (
              <Tag icon={<ThunderboltOutlined />} color="warning">
                已降级
              </Tag>
            ) : (
              <Tag icon={<CheckCircleOutlined />} color="success">
                直接执行
              </Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(session.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {session.error ? (
              <Tag icon={<ExclamationCircleOutlined />} color="error">
                错误
              </Tag>
            ) : (
              <Tag icon={<CheckCircleOutlined />} color="success">
                成功
              </Tag>
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {session.error && (
        <Alert message="规划错误" description={session.error} type="error" showIcon />
      )}

      {session.parsed_plan && (
        <Card size="small">
          <Title level={5}>
            <ExperimentOutlined /> 计划：{session.parsed_plan.intent}
          </Title>
          <PlanStepsPanel steps={session.parsed_plan.steps} />
        </Card>
      )}

      <Divider style={{ margin: '8px 0' }} />
      <PromptPanel prompt={session.prompt} />
      <RawResponsePanel rawResponse={session.raw_response} />
      <AgentSelectionPanel
        selectedAgents={session.selected_agents}
        capabilities={session.capabilities}
      />
    </Space>
  )
}
