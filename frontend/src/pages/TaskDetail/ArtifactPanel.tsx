import { useState } from "react"
import { Card, List, Tag, Typography, Empty, Space, Spin, Button, Modal, Descriptions, Popconfirm, message, Image } from "antd"
import {
  FileTextOutlined,
  CodeOutlined,
  LinkOutlined,
  OrderedListOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  PictureOutlined,
  FileUnknownOutlined,
} from "@ant-design/icons"
import type { ArtifactItem } from "../../api/artifacts"
import { useTaskArtifacts, useDeleteArtifact } from "../../hooks/useArtifacts"
import { useNavigate } from "react-router-dom"

const { Text, Paragraph, Title } = Typography

const typeConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  text: { color: "blue", icon: <FileTextOutlined /> },
  markdown: { color: "purple", icon: <FileTextOutlined /> },
  json: { color: "green", icon: <CodeOutlined /> },
  list: { color: "orange", icon: <OrderedListOutlined /> },
  url: { color: "cyan", icon: <LinkOutlined /> },
  image_url: { color: "magenta", icon: <PictureOutlined /> },
}

function renderArtifactContent(artifact: ArtifactItem) {
  switch (artifact.type) {
    case "url":
      return (
        <a href={artifact.content} target="_blank" rel="noreferrer">
          {artifact.content}
        </a>
      )
    case "image_url":
      return <Image src={artifact.content} width={200} fallback="" />
    case "json":
      try {
        const parsed = JSON.parse(artifact.content)
        return (
          <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 12, maxHeight: 300, overflow: "auto" }}>
            {JSON.stringify(parsed, null, 2)}
          </pre>
        )
      } catch {
        return <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 12 }}>{artifact.content}</pre>
      }
    case "list":
      try {
        const items = JSON.parse(artifact.content)
        if (Array.isArray(items)) {
          return (
            <List
              size="small"
              bordered
              dataSource={items}
              renderItem={(item: unknown) => (
                <List.Item style={{ padding: "4px 12px" }}>
                  <Text>{typeof item === "string" ? item : JSON.stringify(item)}</Text>
                </List.Item>
              )}
            />
          )
        }
      } catch { /* fall through */ }
      return <Paragraph>{artifact.content}</Paragraph>
    case "markdown":
      return (
        <pre style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
          {artifact.content}
        </pre>
      )
    default:
      return <Paragraph>{artifact.content}</Paragraph>
  }
}

function SourceMetadata({ artifact }: { artifact: ArtifactItem }) {
  const meta = artifact.metadata || {}
  const stepId = meta.step_id as string | undefined
  const agentId = (meta.created_by as string) || artifact.owner
  const taskId = meta.task_id as string | undefined
  const navigate = useNavigate()
  return (
    <Space size={8} wrap>
      {agentId && <Tag color="blue">Agent: {agentId}</Tag>}
      {stepId && <Tag color="green">Step: {stepId}</Tag>}
      {taskId && (
        <Tag color="default" style={{ cursor: "pointer" }} onClick={() => navigate(`/tasks/${taskId}`)}>
          Task: {taskId.slice(0, 12)}...
        </Tag>
      )}
    </Space>
  )
}

function ArtifactCard({ artifact, taskId, onView }: { artifact: ArtifactItem; taskId: string; onView: (a: ArtifactItem) => void }) {
  const cfg = typeConfig[artifact.type] || { color: "default", icon: <FileUnknownOutlined /> }
  const deleteMutation = useDeleteArtifact(taskId)

  return (
    <Card
      size="small"
      title={
        <Space>
          {cfg.icon}
          <span>{artifact.name}</span>
          <Tag color={cfg.color}>{artifact.type}</Tag>
        </Space>
      }
      extra={
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => onView(artifact)} />
          <Popconfirm
            title="确定删除该产物？"
            onConfirm={() => deleteMutation.mutate(artifact.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} loading={deleteMutation.isPending} />
          </Popconfirm>
        </Space>
      }
      style={{ marginBottom: 12 }}
    >
      <SourceMetadata artifact={artifact} />
      <div style={{ marginTop: 8 }}>
        {renderArtifactContent(artifact)}
      </div>
    </Card>
  )
}

interface ArtifactPanelProps {
  taskId: string | null
}

export default function ArtifactPanel({ taskId }: ArtifactPanelProps) {
  const { data, isLoading, error, refetch } = useTaskArtifacts(taskId)
  const [viewing, setViewing] = useState<ArtifactItem | null>(null)

  if (!taskId) return null

  if (isLoading) {
    return <Spin style={{ display: "block", margin: "40px auto" }} />
  }

  if (error) {
    return (
      <Space direction="vertical" style={{ width: "100%" }}>
        <Text type="error">加载产物失败</Text>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重试</Button>
      </Space>
    )
  }

  const artifacts = data?.artifacts || []

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Title level={5} style={{ margin: 0 }}>
          Artifacts ({data?.total || 0})
        </Title>
        <Button icon={<ReloadOutlined />} size="small" onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      {artifacts.length === 0 ? (
        <Empty description="暂无产物" />
      ) : (
        artifacts.map((a) => (
          <ArtifactCard key={a.id} artifact={a} taskId={taskId} onView={setViewing} />
        ))
      )}

      {/* Detail Modal */}
      <Modal
        title={viewing?.name || "产物详情"}
        open={!!viewing}
        onCancel={() => setViewing(null)}
        footer={null}
        width={640}
      >
        {viewing && (
          <Space direction="vertical" size="middle" style={{ width: "100%" }}>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="ID"><Text code>{viewing.id}</Text></Descriptions.Item>
              <Descriptions.Item label="类型"><Tag color={typeConfig[viewing.type]?.color || "default"}>{viewing.type}</Tag></Descriptions.Item>
              <Descriptions.Item label="名称">{viewing.name}</Descriptions.Item>
              <Descriptions.Item label="创建者">{viewing.owner}</Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>{new Date(viewing.created_at).toLocaleString("zh-CN")}</Descriptions.Item>
            </Descriptions>
            <SourceMetadata artifact={viewing} />
            <Title level={5}>内容</Title>
            {renderArtifactContent(viewing)}
          </Space>
        )}
      </Modal>
    </Space>
  )
}