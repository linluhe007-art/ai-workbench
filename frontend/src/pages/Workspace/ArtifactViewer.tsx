import { Card, Descriptions, Tag, Typography, Button, Space, Collapse, Empty, Image } from "antd"
import { CloseOutlined, LinkOutlined } from "@ant-design/icons"
import { useNavigate } from "react-router-dom"
import type { WorkspaceItemData } from "../../api/workspaces"

const { Text, Paragraph, Title } = Typography

interface ArtifactViewerProps {
  item: WorkspaceItemData | null
  onClose: () => void
}

function renderContent(item: WorkspaceItemData) {
  const { type, content } = item
  if (content === null || content === undefined) {
    return <Text type="secondary">(empty)</Text>
  }
  switch (type) {
    case "text":
      return (
        <Card size="small" style={{ background: "#fafafa", maxHeight: 400, overflow: "auto" }}>
          <Paragraph style={{ whiteSpace: "pre-wrap", margin: 0 }}>{String(content)}</Paragraph>
        </Card>
      )
    case "markdown":
      return (
        <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
          {String(content)}
        </pre>
      )
    case "json":
    case "dict":
      return (
        <Card size="small" style={{ background: "#fafafa", maxHeight: 400, overflow: "auto" }}>
          <pre style={{ margin: 0, fontSize: 13 }}>
            {typeof content === "string" ? (() => { try { return JSON.stringify(JSON.parse(content), null, 2) } catch { return content } })() : JSON.stringify(content, null, 2)}
          </pre>
        </Card>
      )
    case "list":
      return (
        <Card size="small" style={{ background: "#fafafa", maxHeight: 400, overflow: "auto" }}>
          {Array.isArray(content) ? (
            <ol style={{ margin: 0, paddingLeft: 20 }}>
              {content.map((c, i) => <li key={i}>{typeof c === "object" ? JSON.stringify(c) : String(c)}</li>)}
            </ol>
          ) : (
            <pre>{JSON.stringify(content, null, 2)}</pre>
          )}
        </Card>
      )
    case "image_url":
      return <Image src={String(content)} width={300} fallback="" />
    case "url":
      return <a href={String(content)} target="_blank" rel="noreferrer">{String(content)}</a>
    default:
      return (
        <Card size="small" style={{ background: "#fafafa" }}>
          <pre>{typeof content === "string" ? content : JSON.stringify(content, null, 2)}</pre>
        </Card>
      )
  }
}

export default function ArtifactViewer({ item, onClose }: ArtifactViewerProps) {
  const navigate = useNavigate()
  if (!item) {
    return <Empty description="请选择要查看的产物" />
  }

  const meta = item.metadata || {}
  const sourceTaskId = meta.task_id as string | undefined
  const sourceStepId = meta.step_id as string | undefined
  const sourceAgentId = (meta.created_by as string) || item.owner

  return (
    <Card
      title={<Space>{item.name}<Tag>{item.type}</Tag></Space>}
      extra={<Button icon={<CloseOutlined />} onClick={onClose} size="small" />}
      size="small"
    >
      <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="ID"><Text code>{item.id}</Text></Descriptions.Item>
        <Descriptions.Item label="创建者"><Tag>{item.owner}</Tag></Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(item.created_at).toLocaleString("zh-CN")}</Descriptions.Item>
        {sourceAgentId && <Descriptions.Item label="来源 Agent"><Tag color="blue">{sourceAgentId}</Tag></Descriptions.Item>}
        {sourceStepId && <Descriptions.Item label="来源步骤"><Tag color="green">{sourceStepId}</Tag></Descriptions.Item>}
        {sourceTaskId && (
          <Descriptions.Item label="来源任务">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              onClick={() => navigate(`/tasks/${sourceTaskId}`)}
            >
              {sourceTaskId}
            </Button>
          </Descriptions.Item>
        )}
      </Descriptions>

      {item.metadata && Object.keys(item.metadata).length > 0 && (
        <Collapse
          size="small"
          style={{ marginBottom: 16 }}
          items={[{
            key: "meta",
            label: `Metadata (${Object.keys(item.metadata).length} fields)`,
            children: <pre style={{ fontSize: 12, margin: 0 }}>{JSON.stringify(item.metadata, null, 2)}</pre>,
          }]}
        />
      )}

      <Title level={5}>内容</Title>
      {renderContent(item)}
    </Card>
  )
}