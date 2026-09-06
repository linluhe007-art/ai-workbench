import React, { useState } from "react"
import {
  Card, Col, Row, Statistic, Typography, Tag, Alert, Spin,
  Button, Table, Space, message, Descriptions, Input, Select,
  Modal, Badge,
} from "antd"
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons"
import {
  useModels, useProviders, useConfigureModel, useTestModel, useGenerateWithModel,
} from "../../hooks/useModels"
import type {
  RoutingTableEntry, ModelConfigInfo, AvailableModel,
} from "../../api/models"
import DeepSeekPanel from "./DeepSeekPanel"

const { Title, Text } = Typography

const providerLabels: Record<string, string> = {
  ollama: "Ollama",
  llama_cpp: "llama.cpp",
  openai_compatible: "OpenAI Compatible",
}

const providerColors: Record<string, string> = {
  ollama: "green",
  llama_cpp: "blue",
  openai_compatible: "purple",
}

const ModelSettingsPage: React.FC = () => {
  const { data, isLoading, error, refetch } = useModels()
  const { data: providersData } = useProviders()
  const configureMut = useConfigureModel()
  const testMut = useTestModel()
  const generateMut = useGenerateWithModel()

  const [modalOpen, setModalOpen] = useState(false)
  const [editProvider, setEditProvider] = useState("ollama")
  const [edit接口地址, setEdit接口地址] = useState("")
  const [editApiKey, setEditApiKey] = useState("")
  const [testResults, setTestResults] = useState<Record<string, boolean | null>>({})

  const [generateOpen, setGenerateOpen] = useState(false)
  const [gen提示词, setGen提示词] = useState("")
  const [genCategory, setGenCategory] = useState("chat")
  const [genResult, setGenResult] = useState<string | null>(null)

  const handleConfigure = async () => {
    try {
      await configureMut.mutateAsync({
        provider_type: editProvider,
        endpoint: edit接口地址 || undefined,
        api_key: editApiKey || undefined,
      })
      message.success("配置成功")
      setModalOpen(false)
    } catch {
      message.error("配置失败")
    }
  }

  const handleTest = async (providerType: string) => {
    try {
      const res = await testMut.mutateAsync(providerType)
      setTestResults((prev) => ({ ...prev, [providerType]: res.connected }))
      message.success(res.connected ? "已连接" : "Failed")
    } catch {
      setTestResults((prev) => ({ ...prev, [providerType]: false }))
    }
  }

  const handleGenerate = async () => {
    if (!gen提示词.trim()) return
    try {
      const res = await generateMut.mutateAsync({
        task_category: genCategory,
        prompt: gen提示词,
      })
      setGenResult(res.response.text)
    } catch {
      message.error("生成失败")
    }
  }

  if (isLoading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>
  }

  const routingEntries: [string, RoutingTableEntry][] = data?.routing_table
    ? Object.entries(data.routing_table)
    : []

  const configs = data?.configs || []
  const availableModels = data?.available_models || []

  const routingCols = [
    { title: "任务分类", dataIndex: "category", key: "category", width: 120,
      render: (_: unknown, r: [string, RoutingTableEntry]) => <Tag>{r[0]}</Tag> },
    { title: "模型", dataIndex: "model", key: "model", render: (_: unknown, r: [string, RoutingTableEntry]) => r[1].model_name },
    {
      title: "服务提供方", dataIndex: "provider", key: "provider", width: 160,
      render: (_: unknown, r: [string, RoutingTableEntry]) => (
        <Tag color={providerColors[r[1].provider_type]}>{providerLabels[r[1].provider_type] || r[1].provider_type}</Tag>
      ),
    },
    { title: "隐私级别", dataIndex: "privacy", key: "privacy", width: 80,
      render: (_: unknown, r: [string, RoutingTableEntry]) => <Tag>{r[1].privacy_level}</Tag> },
    { title: "成本", dataIndex: "cost", key: "cost", width: 80,
      render: (_: unknown, r: [string, RoutingTableEntry]) => r[1].estimated_cost },
  ]

  return (
    <div>
      <DeepSeekPanel />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <SettingOutlined /> Model Settings
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
          <Button type="primary" icon={<ApiOutlined />} onClick={() => setModalOpen(true)}>
            Configure Provider
          </Button>
        </Space>
      </div>

      {error ? <Alert type="error" message="加载失败" showIcon /> : null}

      <Row gutter={16}>
        <Col xs={24} lg={16}>
          <Card title={<span><ThunderboltOutlined /> Routing Table</span>} style={{ marginBottom: 16 }}>
            <Table
              columns={routingCols}
              dataSource={routingEntries}
              rowKey={(r) => r[0]}
              pagination={false}
              size="small"
            />
          </Card>

          <Card title="可用模型" style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              {availableModels.map((m: AvailableModel) => (
                <Col key={m.name} xs={12} sm={8}>
                  <Card size="small">
                    <Text strong>{m.name}</Text>
                    <br />
                    <Tag color={providerColors[m.provider]}>{providerLabels[m.provider] || m.provider}</Tag>
                    <Tag>{m.privacy_level}</Tag>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {m.task_categories.join(", ")}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="服务提供方状态" style={{ marginBottom: 16 }}>
            {["ollama", "llama_cpp", "openai_compatible"].map((pt) => {
              const config = configs.find((c: ModelConfigInfo) => c.provider_type === pt)
              const testOk = testResults[pt]
              return (
                <Card key={pt} size="small" style={{ marginBottom: 8 }}>
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Space>
                      <Tag color={providerColors[pt]}>{providerLabels[pt] || pt}</Tag>
                      {testOk === true ? <Badge status="success" text="已连接" /> : testOk === false ? <Badge status="error" text="失败" /> : <Badge status="default" text="未知" />}
                    </Space>
                    {config?.endpoint ? <Text type="secondary" style={{ fontSize: 12 }}>接口地址: {config.endpoint}</Text> : null}
                    <Space>
                      <Button size="small" onClick={() => handleTest(pt)} loading={testMut.isPending}>
                        Test
                      </Button>
                      <Button size="small" onClick={() => { setEditProvider(pt); setEdit接口地址(config?.endpoint || ""); setModalOpen(true) }}>
                        Configure
                      </Button>
                    </Space>
                  </Space>
                </Card>
              )
            })}
          </Card>

          <Card title="快速测试" extra={
            <Button size="small" icon={<PlayCircleOutlined />} onClick={() => setGenerateOpen(true)}>
              Generate
            </Button>
          }>
            {genResult ? (
              <Alert type="success" message="已生成" description={genResult.slice(0, 300)} />
            ) : (
              <Text type="secondary">点击生成以测试模型。</Text>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="配置服务提供方"
        open={modalOpen}
        onOk={handleConfigure}
        onCancel={() => setModalOpen(false)}
        confirmLoading={configureMut.isPending}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <div style={{ marginBottom: 4 }}>服务提供方类型</div>
            <Select
              value={editProvider}
              onChange={setEditProvider}
              style={{ width: "100%" }}
              options={[
                { value: "ollama", label: "Ollama" },
                { value: "llama_cpp", label: "llama.cpp" },
                { value: "openai_compatible", label: "OpenAI Compatible" },
              ]}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>接口地址</div>
            <Input
              placeholder="http://localhost:11434"
              value={edit接口地址}
              onChange={(e) => setEdit接口地址(e.target.value)}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>API Key (optional)</div>
            <Input.Password
              placeholder="sk-..."
              value={editApiKey}
              onChange={(e) => setEditApiKey(e.target.value)}
            />
          </div>
        </Space>
      </Modal>

      <Modal
        title="生成测试"
        open={generateOpen}
        onOk={handleGenerate}
        onCancel={() => setGenerateOpen(false)}
        confirmLoading={generateMut.isPending}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <div style={{ marginBottom: 4 }}>任务分类</div>
            <Select
              value={genCategory}
              onChange={setGenCategory}
              style={{ width: "100%" }}
              options={[
                { value: "chat", label: "对话" },
                { value: "coding", label: "编程" },
                { value: "research", label: "研究" },
                { value: "writing", label: "写作" },
                { value: "analysis", label: "分析" },
              ]}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>提示词</div>
            <Input.TextArea
              placeholder="输入你的提示词..."
              value={gen提示词}
              onChange={(e) => setGen提示词(e.target.value)}
              rows={3}
            />
          </div>
        </Space>
      </Modal>
    </div>
  )
}

export default ModelSettingsPage
