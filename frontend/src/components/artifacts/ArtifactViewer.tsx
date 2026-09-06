import { Card, Descriptions, Tag, Typography, Button, Space, Collapse, Empty, Image } from "antd"
import { CloseOutlined, LinkOutlined } from "@ant-design/icons"
import { useNavigate } from "react-router-dom"

const { Text, Paragraph, Title } = Typography

export interface ArtifactViewerData {
  id: string
  name: string
  type: string
  content: string
  owner: string
  metadata: Record<string, unknown>
  created_at: string
  workspace_id?: string
}

interface ArtifactViewerProps {
  item: ArtifactViewerData | null
  onClose?: () => void
}

export function renderArtifactContent(type: string, content: string | unknown) {
  if (content === null || content === undefined) {
    return <Text type="secondary">(empty)</Text>
  }
  const str = typeof content === "string" ? content : JSON.stringify(content)
  switch (type) {
    case "url":
      return <a href={str} target="_blank" rel="noreferrer">{str}</a>
    case "image_url":
      return <Image src={str} width={300} fallback="" />
    case "json":
      try {
        return <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 12, maxHeight: 300, overflow: "auto" }}>{JSON.stringify(JSON.parse(str), null, 2)}</pre>
      } catch {
        return <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 12 }}>{str}</pre>
      }
    case "list":
      try {
        const items = JSON.parse(str)
        if (Array.isArray(items)) {
          return <ol style={{ margin: 0, paddingLeft: 20 }}>{items.map((c: unknown, i: number) => <li key={i}>{typeof c === "string" ? c : JSON.stringify(c)}</li>)}</ol>
        }
      } catch { /* fall through */ }
      return <Paragraph>{str}</Paragraph>
    case "markdown":
      return <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>{str}</pre>
    default:
      return <Paragraph>{str}</Paragraph>
  }
}

export default function ArtifactViewer({ item, onClose }: ArtifactViewerProps) {
  const navigate = useNavigate()
  if (!item) return <Empty description="请选择要查看的产物" />

  const meta = item.metadata || {}
  const sourceTaskId = meta.task_id as string | undefined
  const sourceStepId = meta.step_id as string | undefined
  const sourceAgentId = (meta.created_by as string) || item.owner

  return (
    <Card
      title={<Space>{item.name}<Tag>{item.type}</Tag></Space>}
      extra={onClose ? <Button icon={<CloseOutlined />} onClick={onClose} size="small" /> : null}
      size="small"
    >
      <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="ID"><Text code>{item.id}</Text></Descriptions.Item>
        <Descriptions.Item label="创建者"><Tag>{item.owner}</Tag></Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(item.created_at).toLocaleString("zh-CN")}</Descriptions.Item>
        {sourceAgentId && <Descriptions.Item label="Agent"><Tag color="blue">{sourceAgentId}</Tag></Descriptions.Item>}
        {sourceStepId && <Descriptions.Item label="步骤"><Tag color="green">{sourceStepId}</Tag></Descriptions.Item>}
        {sourceTaskId && (
          <Descriptions.Item label="任务">
            <Button type="link" size="small" icon={<LinkOutlined />} onClick={() => navigate(`/tasks/${sourceTaskId}`)}>{sourceTaskId}</Button>
          </Descriptions.Item>
        )}
      </Descriptions>
      {item.metadata && Object.keys(item.metadata).length > 0 && (
        <Collapse size="small" style={{ marginBottom: 16 }} items={[{ key: "meta", label: `Metadata (${Object.keys(item.metadata).length})`, children: <pre style={{ fontSize: 12, margin: 0 }}>{JSON.stringify(item.metadata, null, 2)}</pre> }]} />
      )}
      <Title level={5}>内容</Title>
      {renderArtifactContent(item.type, item.content)}
    </Card>
  )
}