import React, { useState } from "react"
import { Card, Col, Row, Typography, Tag, Spin, Alert, Table, Statistic, Input, Button, Space, Tabs, Descriptions, Progress } from "antd"
import { SearchOutlined, BugOutlined, ReloadOutlined, ApiOutlined, ThunderboltOutlined, CodeOutlined } from "@ant-design/icons"
import { useTraces, useDebugPrompts, useAIUsage, useAISummary, useTaskTrace } from "../../hooks/useAIDebug"
import type { DecisionTrace, PromptInfo, AIUsageRecord } from "../../api/aiDebug"

const { Title, Text } = Typography

const traceTypeColors: Record<string, string> = {
  command_analysis: "blue", plan_generation: "purple", memory_retrieval: "green",
  agent_selection: "orange", workflow_selection: "cyan", tool_selection: "magenta",
  final_result: "red",
}

// ===== DecisionTraceViewer =====
const DecisionTraceViewer: React.FC = () => {
  const [taskId, setTaskId] = useState("")
  const [searchTaskId, setSearchTaskId] = useState("")
  const { data, isLoading } = useTraces()
  const { data: taskData } = useTaskTrace(searchTaskId || null)

  const traces = data?.traces || []
  const columns = [
    { title: "类型", dataIndex: "trace_type", key: "type", width: 160, render: (t: string) => <Tag color={traceTypeColors[t] || "default"}>{t}</Tag> },
    { title: "组件", dataIndex: "component", key: "comp", width: 120 },
    { title: "任务 ID", dataIndex: "task_id", key: "tid", ellipsis: true, width: 140 },
    { title: "原因", dataIndex: "reason", key: "reason", ellipsis: true },
    { title: "置信度", dataIndex: "confidence", key: "conf", width: 100, render: (v: number) => `${(v * 100).toFixed(0)}%` },
    { title: "时间", dataIndex: "created_at", key: "time", width: 180, render: (t: string) => t?.slice(0, 19).replace("T", " ") },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="任务 ID" value={taskId} onChange={e => setTaskId(e.target.value)} style={{ width: 250 }} />
        <Button icon={<SearchOutlined />} onClick={() => setSearchTaskId(taskId)}>搜索</Button>
        <Button icon={<ReloadOutlined />} onClick={() => setSearchTaskId(taskId)}>刷新</Button>
      </Space>
      {taskData && (
        <Alert type="info" message={`任务 ${searchTaskId}：共找到 ${taskData.total} 条轨迹`} style={{ marginBottom: 8 }} />
      )}
      <Table columns={columns} dataSource={traces} rowKey="id" loading={isLoading} size="small" pagination={{ pageSize: 20 }} />
    </div>
  )
}

// ===== PromptViewer =====
const PromptViewer: React.FC = () => {
  const { data, isLoading } = useDebugPrompts()
  const prompts = data?.prompts || []
  const cols = [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "版本", dataIndex: "version", key: "ver", width: 60 },
    { title: "是否启用", dataIndex: "active", key: "active", width: 80, render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? "Yes" : "No"}</Tag> },
    { title: "变量", dataIndex: "variables", key: "vars", render: (v: string[]) => v?.join(", ") || "-" },
    { title: "内容", dataIndex: "content", key: "content", ellipsis: true, width: 300 },
    { title: "创建时间", dataIndex: "created_at", key: "time", width: 170, render: (t: string) => t?.slice(0, 19).replace("T", " ") },
  ]
  return <Table columns={cols} dataSource={prompts} rowKey="id" loading={isLoading} size="small" pagination={false} />
}

// ===== UsagePanel =====
const UsagePanel: React.FC = () => {
  const { data: summary } = useAISummary()
  const { data: usageData } = useAIUsage()
  const recs = usageData?.records || []
  const cols = [
    { title: "模型", dataIndex: "model", key: "model" },
    { title: "服务提供方", dataIndex: "provider", key: "prov" },
    { title: "输入 Token", dataIndex: "tokens_input", key: "tin" },
    { title: "输出 Token", dataIndex: "tokens_output", key: "tout" },
    { title: "延迟", dataIndex: "latency_ms", key: "lat", render: (v: number) => `${v}ms` },
    { title: "成本", dataIndex: "cost", key: "cost" },
    { title: "任务", dataIndex: "task_id", key: "tid", ellipsis: true },
  ]
  return (
    <div>
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Statistic title="记录总数" value={summary.summary.total_records} /></Col>
          <Col span={6}><Statistic title="Token 总数" value={summary.summary.total_tokens} /></Col>
          <Col span={6}><Statistic title="平均延迟" value={summary.summary.average_latency_ms} suffix="ms" /></Col>
          <Col span={6}><Statistic title="总成本" value={`$${summary.summary.total_cost.toFixed(4)}`} /></Col>
        </Row>
      )}
      <Table columns={cols} dataSource={recs} rowKey="id" size="small" pagination={{ pageSize: 15 }} />
    </div>
  )
}

// ===== Main Page =====
const AIDebugCenter: React.FC = () => (
  <div>
    <Title level={3}><BugOutlined /> AI 调试中心</Title>
    <Tabs defaultActiveKey="trace" items={[
      { key: "trace", label: <span><ApiOutlined /> 决策轨迹</span>, children: <DecisionTraceViewer /> },
      { key: "prompt", label: <span><CodeOutlined /> 提示词库</span>, children: <PromptViewer /> },
      { key: "usage", label: <span><ThunderboltOutlined /> Token 用量</span>, children: <UsagePanel /> },
    ]} />
  </div>
)

export default AIDebugCenter
