import React, { useState } from "react"
import {
  Card, Col, Row, Statistic, Typography, Tag, Alert, Spin,
  Button, Table, Progress, Space, message, Descriptions, Badge,
} from "antd"
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  RiseOutlined,
  TrophyOutlined,
  WarningOutlined,
  BulbOutlined,
  PlayCircleOutlined,
  UndoOutlined,
  ReloadOutlined,
} from "@ant-design/icons"
import {
  useImprovementReport,
  useApplyImprovement,
  useImprovementHistory,
  useRevertImprovement,
} from "../../hooks/useImprovement"
import type {
  StrategyRecommendation,
  AgentPerformance,
  OptimizationRecord,
} from "../../api/improvement"

const { Title, Text, Paragraph } = Typography

const categoryColors: Record<string, string> = {
  agent_selection: "blue",
  retry: "orange",
  workflow: "purple",
  bottleneck: "red",
  resource: "green",
}

const priorityColors: Record<number, string> = {
  0: "default",
  1: "blue",
  2: "red",
}

const priorityLabels: Record<number, string> = {
  0: "低",
  1: "中",
  2: "高",
}

const statusColors: Record<string, string> = {
  applied: "green",
  reverted: "orange",
  pending: "blue",
}

// ===== Analysis Card =====

const AnalysisCard: React.FC<{ analysis: import("../../api/improvement").AnalysisData }> = ({ analysis }) => (
  <Card title={<span><RiseOutlined /> Performance Analysis</span>} style={{ marginBottom: 16 }}>
    <Row gutter={[16, 16]}>
      <Col span={6}>
        <Statistic title="任务总数" value={analysis.task_analysis.total_tasks} />
      </Col>
      <Col span={6}>
        <Statistic
          title="已完成"
          value={analysis.task_analysis.completed_tasks}
          valueStyle={{ color: "#3f8600" }}
          prefix={<CheckCircleOutlined />}
        />
      </Col>
      <Col span={6}>
        <Statistic
          title="失败"
          value={analysis.task_analysis.failed_tasks}
          valueStyle={{ color: analysis.task_analysis.failed_tasks > 0 ? "#cf1322" : undefined }}
          prefix={<ExclamationCircleOutlined />}
        />
      </Col>
      <Col span={6}>
        <Statistic
          title="成功率"
          value={analysis.task_analysis.success_rate * 100}
          precision={1}
          suffix="%"
        />
      </Col>
    </Row>
    <div style={{ marginTop: 16 }}>
      <Progress
        percent={Math.round(analysis.task_analysis.success_rate * 100)}
        status={analysis.task_analysis.success_rate >= 0.8 ? "success" : "active"}
      />
    </div>
    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col span={8}>
        <Statistic
          title="平均耗时"
          value={analysis.task_analysis.average_duration_ms}
          precision={0}
          suffix="ms"
        />
      </Col>
      <Col span={8}>
        <Statistic title="最佳 Agent" value={analysis.best_agent || "-"} />
      </Col>
      <Col span={8}>
        <Statistic title="最差 Agent" value={analysis.worst_agent || "-"} />
      </Col>
    </Row>
    {analysis.bottlenecks.length > 0 && (
      <div style={{ marginTop: 16 }}>
        <Text strong>瓶颈：</Text>
        {analysis.bottlenecks.map((b, i) => (
          <Alert
            key={i}
            type={b.severity === "high" ? "error" : "warning"}
            message={`${b.type}: ${b.suggestion}`}
            style={{ marginTop: 8 }}
          />
        ))}
      </div>
    )}
  </Card>
)

// ===== Agent Performance Table =====

const AgentPerformanceTable: React.FC<{ agents: AgentPerformance[] }> = ({ agents }) => {
  if (agents.length === 0) return null
  const cols = [
    { title: "Agent", dataIndex: "agent_id", key: "agent_id" },
    { title: "执行次数", dataIndex: "executions", key: "executions" },
    { title: "错误数", dataIndex: "errors", key: "errors" },
    {
      title: "成功率",
      dataIndex: "success_rate",
      key: "success_rate",
      render: (v: number) => (
        <Progress percent={Math.round(v * 100)} size="small" status={v >= 0.8 ? "success" : "active"} />
      ),
    },
  ]
  return (
    <Card title="Agent 表现" style={{ marginBottom: 16 }}>
      <Table columns={cols} dataSource={agents} rowKey="agent_id" pagination={false} size="small" />
    </Card>
  )
}

// ===== Recommendations Panel =====

const RecommendationsPanel: React.FC<{
  recommendations: StrategyRecommendation[]
  onApply: (ids: string[]) => void
  loading: boolean
}> = ({ recommendations, onApply, loading }) => (
  <Card
    title={<span><BulbOutlined /> Strategy Recommendations</span>}
    extra={
      <Button
        type="primary"
        size="small"
        icon={<PlayCircleOutlined />}
        loading={loading}
        onClick={() => onApply([])}
      >
        Apply All
      </Button>
    }
    style={{ marginBottom: 16 }}
  >
    {recommendations.length === 0 ? (
      <Text type="secondary">暂无优化建议，执行任务后将自动生成洞察。</Text>
    ) : (
      recommendations.map((rec) => (
        <Card
          key={rec.id}
          size="small"
          style={{ marginBottom: 8 }}
          title={
            <Space>
              <Tag color={categoryColors[rec.category] || "default"}>{rec.category}</Tag>
              <Tag color={priorityColors[rec.priority]}>{priorityLabels[rec.priority]}</Tag>
              {rec.title}
            </Space>
          }
          extra={
            <Button size="small" onClick={() => onApply([rec.id])} loading={loading}>
              Apply
            </Button>
          }
        >
          <Paragraph>{rec.description}</Paragraph>
          <Text type="secondary">Expected: {rec.expected_impact}</Text>
        </Card>
      ))
    )}
  </Card>
)

// ===== History Panel =====

const HistoryPanel: React.FC<{
  records: OptimizationRecord[]
  onRevert: (id: string) => void
  loading: boolean
}> = ({ records, onRevert, loading }) => {
  if (records.length === 0) return null
  const cols = [
    { title: "标题", dataIndex: "title", key: "title", ellipsis: true },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
      width: 120,
      render: (c: string) => <Tag color={categoryColors[c] || "default"}>{c}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (s: string) => <Badge status={s === "applied" ? "success" : "warning"} text={s} />,
    },
    {
      title: "应用时间",
      dataIndex: "applied_at",
      key: "applied_at",
      width: 180,
      render: (t: string) => t ? new Date(t).toLocaleString("zh-CN") : "-",
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_: unknown, r: OptimizationRecord) =>
        r.status === "applied" ? (
          <Button size="small" danger icon={<UndoOutlined />} onClick={() => onRevert(r.id)} loading={loading}>
            Revert
          </Button>
        ) : null,
    },
  ]
  return (
    <Card title="优化历史">
      <Table columns={cols} dataSource={records} rowKey="id" pagination={{ pageSize: 10 }} size="small" />
    </Card>
  )
}

// ===== Main Page =====

const ImprovementPage: React.FC = () => {
  const { data, isLoading, error } = useImprovementReport()
  const { data: historyData } = useImprovementHistory()
  const applyMut = useApplyImprovement()
  const revertMut = useRevertImprovement()

  const handleApply = async (ids: string[]) => {
    try {
      const res = await applyMut.mutateAsync(ids)
      message.success(`Applied ${res.applied} recommendation(s)`)
    } catch {
      message.error("应用失败")
    }
  }

  const handleRevert = async (id: string) => {
    try {
      await revertMut.mutateAsync(id)
      message.success("已回滚")
    } catch {
      message.error("回滚失败")
    }
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
        <Paragraph style={{ marginTop: 16 }}>正在分析系统性能...</Paragraph>
      </div>
    )
  }

  if (error || !data?.success) {
    return <Alert type="error" message="加载失败" description={error ? String(error) : "未知错误"} showIcon />
  }

  const { analysis, strategy_plan } = data
  const records = historyData?.records || []

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <TrophyOutlined /> Self Improvement
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
            Refresh
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <AnalysisCard analysis={analysis} />
          <AgentPerformanceTable agents={analysis.agent_performance} />
          <HistoryPanel records={records} onRevert={handleRevert} loading={revertMut.isPending} />
        </Col>
        <Col xs={24} lg={10}>
          <RecommendationsPanel
            recommendations={strategy_plan.recommendations}
            onApply={handleApply}
            loading={applyMut.isPending}
          />
        </Col>
      </Row>
    </div>
  )
}

export default ImprovementPage
