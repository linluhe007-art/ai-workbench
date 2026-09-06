import React, { useState } from "react"
import {
  Card, Table, Tag, Input, Button, Space, Typography, Spin, Alert,
  Row, Col, Statistic, Progress, Select, message, Modal, Rate,
} from "antd"
import {
  SearchOutlined, ReloadOutlined, StarOutlined,
  CheckCircleOutlined, CloseCircleOutlined, BulbOutlined,
} from "@ant-design/icons"
import {
  useExperienceSearch, useExperienceStats,
  useRecommendations, useSubmitFeedback,
} from "../../hooks/useExperience"

const { Title, Text } = Typography

const ExperienceExplorer: React.FC = () => {
  const [query, setQuery] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [filterSuccess, setFilterSuccess] = useState<boolean | undefined>(undefined)
  const [feedbackModal, setFeedbackModal] = useState(false)
  const [feedbackTaskId, setFeedbackTaskId] = useState("")
  const [feedbackRating, setFeedbackRating] = useState(0)

  const { data: searchData, isLoading: searchLoading } = useExperienceSearch(searchQuery, filterSuccess)
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useExperienceStats()
  const { data: recs } = useRecommendations(searchQuery)
  const feedbackMut = useSubmitFeedback()

  const handleSearch = () => {
    setSearchQuery(query.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch()
  }

  const handleFeedback = async () => {
    if (!feedbackTaskId) return
    try {
      await feedbackMut.mutateAsync({ taskId: feedbackTaskId, rating: feedbackRating })
      message.success("反馈已提交")
      setFeedbackModal(false)
      refetchStats()
    } catch {
      message.error("提交反馈失败")
    }
  }

  const exp = stats?.experience

  const searchCols = [
    { title: "任务模式", dataIndex: "task_pattern", key: "pattern", render: (t: string) => <Text strong>{t}</Text> },
    { title: "Agent", dataIndex: "agents", key: "agents", render: (a: string[]) => <Space size={4}>{a.map((x) => <Tag key={x}>{x}</Tag>)}</Space> },
    { title: "结果", dataIndex: "success", key: "success", render: (s: boolean) => s ? <Tag color="green" icon={<CheckCircleOutlined />}>成功</Tag> : <Tag color="red" icon={<CloseCircleOutlined />}>失败</Tag> },
    { title: "相关度", dataIndex: "score", key: "score", render: (s: number | undefined) => s !== undefined ? s.toFixed(2) : "-" },
    { title: "时间", dataIndex: "created_at", key: "time", render: (t: string) => t ? new Date(t).toLocaleString() : "-" },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>经验探索</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="记录总数" value={exp?.total_records ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="成功率" value={exp?.success_rate ? (exp.success_rate * 100).toFixed(1) : 0} suffix="%" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="成功次数" value={exp?.success_count ?? 0} valueStyle={{ color: "#3f8600" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="失败次数" value={exp?.failure_count ?? 0} valueStyle={{ color: "#cf1322" }} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Space style={{ width: "100%" }}>
          <Input
            placeholder="搜索任务模式..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
          />
          <Select
            value={filterSuccess}
            onChange={setFilterSuccess}
            style={{ width: 140 }}
            allowClear
            placeholder="结果"
            options={[
              { value: true, label: "成功" },
              { value: false, label: "失败" },
            ]}
          />
          <Button type="primary" onClick={handleSearch} icon={<SearchOutlined />}>搜索</Button>
          <Button onClick={() => setFeedbackModal(true)} icon={<StarOutlined />}>反馈</Button>
          <Button onClick={() => refetchStats()} icon={<ReloadOutlined />}>刷新</Button>
        </Space>
      </Card>

      {recs && recs.recommended_agents.length > 0 && (
        <Card title={<><BulbOutlined /> Recommendations</>} style={{ marginBottom: 16 }}>
          <Space direction="vertical">
            <Text>Recommended Agents: {recs.recommended_agents.map((a) => <Tag key={a} color="blue">{a}</Tag>)}</Text>
            <Text>Historical Success Rate: {(recs.historical_success_rate * 100).toFixed(1)}%</Text>
            {recs.warnings.length > 0 && (
              <Alert type="warning" message={recs.warnings.join("; ")} />
            )}
          </Space>
        </Card>
      )}

      {searchLoading ? (
        <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>
      ) : searchQuery ? (
        <Card title={`Results (${searchData?.total ?? 0})`}>
          <Table dataSource={searchData?.results || []} columns={searchCols} rowKey="task_pattern" pagination={false} size="middle" />
        </Card>
      ) : (
        <Card>
          {statsLoading ? <Spin /> : (
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Title level={5}>高频任务模式</Title>
                <Table
                  dataSource={exp?.top_patterns || []}
                  columns={[
                    { title: "任务模式", dataIndex: "pattern", key: "p" },
                    { title: "次数", dataIndex: "count", key: "c" },
                    { title: "成功率", dataIndex: "success_rate", key: "sr", render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" /> },
                  ]}
                  rowKey="pattern" pagination={false} size="small"
                />
              </Col>
              <Col span={12}>
                <Title level={5}>最佳 Agent</Title>
                <Table
                  dataSource={exp?.top_agents || []}
                  columns={[
                    { title: "Agent", dataIndex: "agent_id", key: "a" },
                    { title: "成功率", dataIndex: "success_rate", key: "sr", render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" /> },
                    { title: "总数", dataIndex: "total", key: "t" },
                  ]}
                  rowKey="agent_id" pagination={false} size="small"
                />
              </Col>
            </Row>
          )}
        </Card>
      )}

      <Modal title="提交反馈" open={feedbackModal} onOk={handleFeedback} onCancel={() => setFeedbackModal(false)}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input placeholder="任务 ID" value={feedbackTaskId} onChange={(e) => setFeedbackTaskId(e.target.value)} />
          <Rate value={feedbackRating} onChange={setFeedbackRating} />
        </Space>
      </Modal>
    </div>
  )
}

export default ExperienceExplorer