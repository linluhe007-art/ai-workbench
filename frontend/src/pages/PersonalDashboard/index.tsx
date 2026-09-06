import React from "react"
import { Card, Col, Row, Statistic, Typography, Tag, Alert, Spin, Progress } from "antd"
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  TrophyOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  RiseOutlined,
} from "@ant-design/icons"
import { usePersonalDashboard } from "../../hooks/usePersonal"
import type { Insight, DailySummary, PersonalMetrics } from "../../api/personal"

const { Title, Text, Paragraph } = Typography

// ========== DailySummary Component ==========

const DailySummary: React.FC<{ summary: DailySummary }> = ({ summary }) => {
  const moodColors: Record<string, string> = {
    productive: "#52c41a",
    idle: "#faad14",
  }
  const moodIcons: Record<string, React.ReactNode> = {
    productive: <RiseOutlined />,
    idle: <ThunderboltOutlined />,
  }
  return (
    <Card
      title={
        <span>
          {moodIcons[summary.mood] || <InfoCircleOutlined />}
          {" "}今日概览
        </span>
      }
      style={{ marginBottom: 16 }}
    >
      <Paragraph style={{ fontSize: 15, marginBottom: 8 }}>{summary.text}</Paragraph>
      {summary.lines.map((line, i) => (
        <Text key={i} type="secondary" style={{ display: "block", fontSize: 13 }}>
          {line}
        </Text>
      ))}
      <Tag color={moodColors[summary.mood] || "default"} style={{ marginTop: 8 }}>
        {summary.mood === "productive" ? "高效模式" : "待命中"}
      </Tag>
    </Card>
  )
}

// ========== AIInsight Component ==========

const AIInsight: React.FC<{ insights: Insight[] }> = ({ insights }) => {
  const typeConfig: Record<string, { color: string; icon: React.ReactNode }> = {
    achievement: { color: "green", icon: <TrophyOutlined /> },
    warning: { color: "red", icon: <WarningOutlined /> },
    tip: { color: "blue", icon: <BulbOutlined /> },
    suggestion: { color: "purple", icon: <InfoCircleOutlined /> },
  }

  const sorted = [...insights].sort((a, b) => b.priority - a.priority)

  return (
    <Card title={<span><BulbOutlined /> AI 洞察</span>} style={{ marginBottom: 16 }}>
      {sorted.length === 0 ? (
        <Text type="secondary">暂无洞察</Text>
      ) : (
        sorted.map((insight, idx) => {
          const cfg = typeConfig[insight.type] || { color: "default", icon: null }
          return (
            <Alert
              key={idx}
              type={insight.type === "warning" ? "warning" : "info"}
              message={
                <span>
                  {cfg.icon} <Tag color={cfg.color} style={{ marginRight: 8 }}>{insight.type}</Tag>
                  {insight.title}
                </span>
              }
              description={insight.message}
              style={{ marginBottom: 8 }}
              showIcon={false}
            />
          )
        })
      )}
    </Card>
  )
}

// ========== ProductivityChart Component ==========

const ProductivityChart: React.FC<{ metrics: PersonalMetrics }> = ({ metrics }) => {
  const successPercent = metrics.tasks_today > 0
    ? Math.round((metrics.tasks_completed_today / metrics.tasks_today) * 100)
    : 0

  return (
    <Card title={<span><RiseOutlined /> 效率仪表盘</span>}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Statistic
            title="今日任务"
            value={metrics.tasks_today}
            prefix={<ThunderboltOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="已完成"
            value={metrics.tasks_completed_today}
            valueStyle={{ color: "#3f8600" }}
            prefix={<CheckCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="失败"
            value={metrics.tasks_failed_today}
            valueStyle={{ color: metrics.tasks_failed_today > 0 ? "#cf1322" : undefined }}
            prefix={<ExclamationCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="运行中"
            value={metrics.tasks_running}
            valueStyle={{ color: "#1890ff" }}
          />
        </Col>
      </Row>

      <div style={{ marginTop: 24 }}>
        <Text strong>成功率</Text>
        <Progress
          percent={successPercent}
          status={successPercent >= 80 ? "success" : successPercent >= 50 ? "active" : "exception"}
          style={{ marginTop: 8 }}
        />
      </div>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Statistic
            title="平均耗时(ms)"
            value={metrics.efficiency.average_duration_ms}
            precision={0}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="总迭代"
            value={metrics.efficiency.total_iterations}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="成功率"
            value={metrics.efficiency.success_rate * 100}
            precision={1}
            suffix="%"
          />
        </Col>
      </Row>

      <Title level={5} style={{ marginTop: 24 }}>知识增长</Title>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Statistic title="新增知识" value={metrics.knowledge_growth.knowledge_items_added} />
        </Col>
        <Col span={8}>
          <Statistic title="经验记录" value={metrics.knowledge_growth.experience_records_created} />
        </Col>
        <Col span={8}>
          <Statistic title="产物生成" value={metrics.knowledge_growth.artifacts_generated} />
        </Col>
      </Row>

      <Title level={5} style={{ marginTop: 24 }}>Agent 活动</Title>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Statistic
            title="活跃 Agent"
            value={metrics.agent_activity.agents_active}
            suffix={`/ ${metrics.agent_activity.agents_total}`}
          />
        </Col>
        <Col span={8}>
          <Statistic title="今日执行" value={metrics.agent_activity.agent_executions_today} />
        </Col>
      </Row>
    </Card>
  )
}

// ========== PersonalDashboard Page ==========

const PersonalDashboard: React.FC = () => {
  const { data, isLoading, error } = usePersonalDashboard()

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
        <Paragraph style={{ marginTop: 16 }}>加载个人仪表盘...</Paragraph>
      </div>
    )
  }

  if (error || !data?.success) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error ? String(error) : "服务暂不可用"}
        showIcon
      />
    )
  }

  const { metrics, insights, daily_summary } = data

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        <ThunderboltOutlined /> 个人控制中心
      </Title>

      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <DailySummary summary={daily_summary} />
          <AIInsight insights={insights} />
        </Col>
        <Col xs={24} lg={12}>
          <ProductivityChart metrics={metrics} />
        </Col>
      </Row>
    </div>
  )
}

export default PersonalDashboard
