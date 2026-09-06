import React from "react"
import { Card, Typography, Table, Tag, Space, Statistic, Row, Col, Spin, Empty, Progress } from "antd"
import { TeamOutlined, TrophyOutlined, ThunderboltOutlined, CheckCircleOutlined } from "@ant-design/icons"
import { usePersonalAgents, useDelegations, useAgentRoles } from "../../hooks/usePersonalAgents"
import type { TeamMember } from "../../api/personalAgents"

const { Title, Paragraph } = Typography

const ROLE_COLORS: Record<string, string> = { research: "purple", coding: "blue", writer: "green", analyst: "orange" }

const AgentTeam: React.FC = () => {
  const { data: teamData, isLoading } = usePersonalAgents()
  const { data: rolesData } = useAgentRoles()
  const { data: delegationsData } = useDelegations()

  const members: TeamMember[] = teamData?.members || []
  const stats = teamData?.stats
  const delegations = delegationsData?.delegations || []

  const columns = [
    { title: "Agent", dataIndex: "name", key: "name", render: (t: string, r: TeamMember) => <Space><Tag color={ROLE_COLORS[r.role]}>{r.role}</Tag>{t}</Space> },
    { title: "能力", dataIndex: "capabilities", key: "caps", render: (caps: string[]) => caps?.map((c) => <Tag key={c}>{c}</Tag>) },
    { title: "任务数", dataIndex: "total_tasks", key: "tasks", width: 80 },
    { title: "成功率", dataIndex: "success_rate", key: "rate", width: 140, render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" /> },
    { title: "平均耗时", dataIndex: "avg_duration_ms", key: "dur", width: 100, render: (v: number) => v > 0 ? (v / 1000).toFixed(1) + "s" : "-" },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={2}><TeamOutlined /> Personal Agent Team</Title>
      <Paragraph type="secondary">Your personal AI agent team with specialized roles for research, coding, writing, and analysis.</Paragraph>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}><Card><Statistic title="团队成员" value={stats.active_members} prefix={<TeamOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="任务总数" value={stats.total_tasks} prefix={<ThunderboltOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="成功次数" value={stats.total_success} prefix={<CheckCircleOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="成功率" value={(stats.overall_success_rate * 100).toFixed(0) + "%"} prefix={<TrophyOutlined />} /></Card></Col>
        </Row>
      )}

      {isLoading ? <Spin /> : members.length === 0 ? <Empty description="暂无团队成员" /> : (
        <Table rowKey="id" dataSource={members} columns={columns} size="middle" pagination={false} />
      )}

      {rolesData?.roles && (
        <Card title="Agent 角色" size="small" style={{ marginTop: 24 }}>
          <Row gutter={16}>
            {rolesData.roles.map((r: { name: string; role: string; description: string; capabilities: string[]; tools: string[] }) => (
              <Col span={6} key={r.role}>
                <Card size="small" title={<Tag color={ROLE_COLORS[r.role]}>{r.name}</Tag>}>
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }}>{r.description}</Paragraph>
                  <Space wrap>{r.capabilities.map((c: string) => <Tag key={c}>{c}</Tag>)}</Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {delegations.length > 0 && (
        <Card title="最近委派" size="small" style={{ marginTop: 24 }}>
          <Table rowKey="id" dataSource={delegations.slice(0, 10)} columns={[
            { title: "任务", dataIndex: "task_id", ellipsis: true },
            { title: "角色", dataIndex: "role", width: 100, render: (r: string) => <Tag color={ROLE_COLORS[r]}>{r}</Tag> },
            { title: "结果", dataIndex: "success", width: 80, render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag color="red">否</Tag> },
            { title: "耗时", dataIndex: "duration_ms", width: 100, render: (v: number) => (v / 1000).toFixed(1) + "s" },
          ]} size="small" pagination={false} />
        </Card>
      )}
    </div>
  )
}

export default AgentTeam
