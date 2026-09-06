import React, { useState } from "react"
import {
  Alert, Button, Card, Descriptions, Input, Space, Spin, Tag, Typography, message,
} from "antd"
import {
  ApiOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons"
import { useLLMConfig, useLLMTest } from "../../hooks/useLLM"
import { getApiRequestId, getFriendlyErrorMessage } from "../../utils/apiError"

const { Title, Text, Paragraph } = Typography

const DeepSeekPanel: React.FC = () => {
  const { data, isLoading, error } = useLLMConfig()
  const testMutation = useLLMTest()
  const [prompt, setPrompt] = useState("请回复：连接成功")
  const [result, setResult] = useState<string | null>(null)

  const handleTest = async () => {
    if (!prompt.trim()) {
      message.warning("请输入测试提示词")
      return
    }
    try {
      const res = await testMutation.mutateAsync({ prompt: prompt.trim() })
      setResult(res.content)
      message.success("连接成功")
    } catch (err) {
      setResult(null)
      const requestId = getApiRequestId(err)
      const friendly = getFriendlyErrorMessage(err, "连接失败")
      message.error(requestId ? friendly + " (request_id: " + requestId + ")" : friendly)
    }
  }

  if (isLoading) {
    return <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
  }

  return (
    <Card
      title={<span><ThunderboltOutlined /> DeepSeek 配置</span>}
      style={{ marginBottom: 16 }}
    >
      {error ? <Alert type="error" message="加载模型配置失败" showIcon style={{ marginBottom: 12 }} /> : null}

      <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Provider">{data?.provider || "-"}</Descriptions.Item>
        <Descriptions.Item label="Model">{data?.model || "-"}</Descriptions.Item>
        <Descriptions.Item label="API Key">
          {data?.api_key_set
            ? <Tag color="green">已配置</Tag>
            : <Tag color="orange">未配置</Tag>}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          {data?.configured
            ? <Tag color="green">可用</Tag>
            : <Tag color="orange">待配置</Tag>}
        </Descriptions.Item>
      </Descriptions>

      <Space direction="vertical" style={{ width: "100%" }}>
        <Input.TextArea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder="输入测试提示词"
        />
        <Button
          type="primary"
          icon={<ApiOutlined />}
          loading={testMutation.isPending}
          onClick={handleTest}
        >
          测试连接
        </Button>
      </Space>

      {result ? (
        <div style={{ marginTop: 16 }}>
          <Text strong><CheckCircleOutlined /> 测试结果</Text>
          <Paragraph style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{result}</Paragraph>
        </div>
      ) : null}
    </Card>
  )
}

export default DeepSeekPanel
