import React, { useState } from "react"
import {
  Card, Col, Row, Statistic, Typography, Tag, Alert, Spin,
  Button, Space, Input, message, Steps, Progress, Badge,
  Timeline, Descriptions,
} from "antd"
import {
  RobotOutlined, ThunderboltOutlined, CheckCircleOutlined,
  SyncOutlined, BulbOutlined, ApiOutlined, TrophyOutlined,
  SendOutlined, ReloadOutlined, DashboardOutlined,
} from "@ant-design/icons"
import { useNavigate } from "react-router-dom"
import { useOSStatus, useOSInsights, useProcessIntent } from "../../hooks/useOS"
import type { OSProcessResult, OrchestrationStep } from "../../api/os"

const { Title, Text, Paragraph } = Typography

const stepStatusIcon: Record<string, React.ReactNode> = {
  completed: <CheckCircleOutlined style={{ color: "#52c41a" }} />,
  running: <SyncOutlined spin style={{ color: "#1890ff" }} />,
  failed: <span style={{ color: "#cf1322" }}>X</span>,
  skipped: <span style={{ color: "#ccc" }}>-</span>,
  pending: <span style={{ color: "#999" }}>...</span>,
}

const actionLabels: Record<string, string> = {
  create_task: "创建任务",
  query: "查询",
  chat: "对话",
  suggest: "建议",
  automate: "自动化",
  improve: "优化",
}

const PersonalOSDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { data: status, isLoading: statusLoading } = useOSStatus()
  const { data: insights, isLoading: insightsLoading } = useOSInsights()
  const processMut = useProcessIntent()

  const [intentInput, setIntentInput] = useState("")
  const [lastResult, setLastResult] = useState<OSProcessResult | null>(null)

  const handleProcess = async () => {
    if (!intentInput.trim()) return
    try {
      const res = await processMut.mutateAsync({ intent: intentInput.trim() })
      setLastResult(res.result)
      message.success(`已处理：${res.result.decision.action}`)
      setIntentInput("")
    } catch {
      message.error("处理失败")
    }
  }

  const state = status?.system_state

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <RobotOutlined /> 个人 AI 工作台
        </Title>
        <Tag color="green">v5.10</Tag>
      </div>

      {/* 全局 AI 输入 */}
      <Card style={{ marginBottom: 16, background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
        <Space.Compact style={{ width: "100%" }}>
          <Input
            size="large"
            placeholder="例如：研究最近 AI Agent 行业趋势，并生成一份报告"
            value={intentInput}
            onChange={(e) => setIntentInput(e.target.value)}
            onPressEnter={handleProcess}
            prefix={<ThunderboltOutlined />}
            style={{ borderRadius: 8 }}
          />
          <Button
            type="primary"
            size="large"
            icon={<SendOutlined />}
            onClick={handleProcess}
            loading={processMut.isPending}
            style={{ borderRadius: 8 }}
          >
            执行任务
          </Button>
        </Space.Compact>
        <Text style={{ color: "rgba(255,255,255,0.8)", fontSize: 12, marginTop: 8, display: "block" }}>
          输入目标，由 AI 自动规划、执行并生成结果。
        </Text>
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={16}>
          {/* 系统状态 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="可用 Agent"
                  value={state?.agents_active ?? 0}
                  suffix={`/ ${state?.agents_available ?? 0}`}
                  prefix={<RobotOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="运行中"
                  value={state?.tasks_running ?? 0}
                  prefix={<SyncOutlined spin={!!state?.tasks_running} />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="排队中"
                  value={state?.tasks_queued ?? 0}
                  prefix={<DashboardOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="健康状态"
                  value={state?.overall_health ?? "healthy"}
                  prefix={<Badge status={state?.overall_health === "healthy" ? "success" : "warning"} />}
                />
              </Card>
            </Col>
          </Row>

          {/* 最近执行流程 */}
          {lastResult && (
            <Card title={<span><ApiOutlined /> 最近执行流程</span>} style={{ marginBottom: 16 }}>
              <Descriptions size="small" column={2} style={{ marginBottom: 12 }}>
                <Descriptions.Item label="目标">{lastResult.user_intent}</Descriptions.Item>
                <Descriptions.Item label="决策">
                  <Tag color="blue">{actionLabels[lastResult.decision.action] || lastResult.decision.action}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="置信度">{(lastResult.decision.confidence * 100).toFixed(0)}%</Descriptions.Item>
                <Descriptions.Item label="任务 ID">{lastResult.task_id || "-"}</Descriptions.Item>
              </Descriptions>
              <Steps
                size="small"
                current={lastResult.steps.filter((s: OrchestrationStep) => s.status === "completed").length}
                items={lastResult.steps.map((s: OrchestrationStep) => ({
                  title: s.name.replace("_", " "),
                  status: s.status === "failed" ? "error" : s.status === "completed" ? "finish" : s.status === "skipped" ? "wait" : "process",
                  description: s.status === "completed" ? `${s.duration_ms.toFixed(0)}ms` : s.error || "",
                }))}
              />
              {lastResult.task_id && (
                <Button type="link" onClick={() => navigate(`/tasks/${lastResult.task_id}`)} style={{ marginTop: 8 }}>
                  查看任务详情 →
                </Button>
              )}
            </Card>
          )}

          {/* 运行中的任务与自动化 */}
          <Card title={<span><SyncOutlined spin /> 活动流程</span>} style={{ marginBottom: 16 }}>
            {statusLoading ? <Spin /> : (
              <Timeline
                items={[
                  { color: "green", children: `${state?.agents_available ?? 0} 个 Agent 可用` },
                  { color: "blue", children: `${state?.tasks_running ?? 0} 个任务运行中` },
                  { color: "orange", children: `${state?.tasks_queued ?? 0} 个任务排队中` },
                  { color: "purple", children: `${state?.automations_running ?? 0} 个自动化活动` },
                ]}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {/* 建议 */}
          <Card title={<span><BulbOutlined /> AI 建议</span>} style={{ marginBottom: 16 }}>
            {insightsLoading ? <Spin /> : (insights?.suggestions || []).map((s, i) => (
              <Alert
                key={i}
                type={s.type === "action" ? "info" : s.type === "tip" ? "success" : "warning"}
                message={s.message}
                style={{ marginBottom: 8 }}
                showIcon={false}
              />
            ))}
          </Card>

          {/* 快捷入口 */}
          <Card title="快捷入口" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Button block icon={<ThunderboltOutlined />} onClick={() => navigate("/command")}>
                开始新任务
              </Button>
              <Button block icon={<ApiOutlined />} onClick={() => navigate("/research")}>
                智能研究
              </Button>
              <Button block icon={<DashboardOutlined />} onClick={() => navigate("/tasks")}>
                查看任务
              </Button>
              <Button block icon={<TrophyOutlined />} onClick={() => navigate("/artifacts")}>
                查看产物
              </Button>
            </Space>
          </Card>

          {/* 系统组件 */}
          <Card title="系统组件">
            {statusLoading ? <Spin /> : status?.components ? (
              Object.entries(status.components).map(([name, s]) => (
                <div key={name} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <Text>{name}</Text>
                  <Badge status="success" text={String(s)} />
                </div>
              ))
            ) : null}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default PersonalOSDashboard
