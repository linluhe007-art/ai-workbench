import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, Input, Button, Typography, Tag, Space, Spin, Alert, List, Divider } from "antd"
import { SendOutlined, HistoryOutlined, BulbOutlined, ThunderboltOutlined } from "@ant-design/icons"
import { useCommandHistory, useProcessCommand } from "../../hooks/useIntelligence"

const { Title, Text, Paragraph } = Typography

const CommandCenter: React.FC = () => {
  const [prompt, set提示词] = useState("")
  const navigate = useNavigate()
  const { data: history } = useCommandHistory()
  const processMut = useProcessCommand()

  const handleSubmit = async () => {
    if (!prompt.trim()) return
    try {
      const result = await processMut.mutateAsync(prompt.trim())
      if (result.task_id) {
        navigate("/tasks/" + result.task_id)
      }
      set提示词("")
    } catch { /* handled by mutation */ }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const historyExamples = history?.history?.slice(-5) || []

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      <Title level={2}><ThunderboltOutlined /> Intelligent Command Center</Title>
      <Paragraph type="secondary">用自然语言描述你想做的事，AI 将理解你的意图并自动创建任务。</Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Input.TextArea
          placeholder='e.g. "例如：研究最近 AI Agent 行业趋势，并生成一份报告"'
          value={prompt}
          onChange={(e) => set提示词(e.target.value)}
          onKeyDown={handleKeyDown}
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ marginBottom: 12 }}
        />
        <Button
          type="primary"
          size="large"
          icon={<SendOutlined />}
          onClick={handleSubmit}
          loading={processMut.isPending}
          block
        >
          Execute Command
        </Button>
      </Card>

      {processMut.isError && (
        <Alert type="error" message="处理命令失败" description={String(processMut.error)} style={{ marginBottom: 16 }} />
      )}

      {processMut.isSuccess && processMut.data && (
        <Card title={<><BulbOutlined /> Intent Analysis</>} style={{ marginBottom: 16 }}>
          <Space direction="vertical">
            <Text><strong>任务类型：</strong> <Tag color="blue">{processMut.data.intent.task_type}</Tag></Text>
            <Text><strong>复杂度：</strong> {processMut.data.intent.complexity}</Text>
            <Text><strong>置信度：</strong> {(processMut.data.confidence * 100).toFixed(0)}%</Text>
            <Text><strong>所需 Agent：</strong> {processMut.data.intent.required_agents.map((a: string) => <Tag key={a}>{a}</Tag>)}</Text>
            <Text><strong>所需工具：</strong> {processMut.data.intent.required_tools.map((t: string) => <Tag key={t} color="green">{t}</Tag>)}</Text>
            {processMut.data.task_id && <Button type="link" onClick={() => navigate("/tasks/" + processMut.data.task_id)}>查看任务</Button>}
          </Space>
        </Card>
      )}

      <Divider />

      <Card title={<><HistoryOutlined /> Recent Commands</>}>
        {historyExamples.length === 0 ? (
          <Text type="secondary">暂无历史命令</Text>
        ) : (
          <List size="small" dataSource={historyExamples} renderItem={(item: Record<string, unknown>) => (
            <List.Item>
              <Space>{String(item.prompt)} <Tag>{String((item.intent as Record<string, unknown>)?.task_type || "unknown")}</Tag></Space>
            </List.Item>
          )} />
        )}
      </Card>
    </div>
  )
}

export default CommandCenter