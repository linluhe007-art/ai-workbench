import { Table, Tag, Space, Button, Popconfirm, Typography, Empty } from "antd"
import { DeleteOutlined, EyeOutlined, FileTextOutlined, CodeOutlined, UnorderedListOutlined, PictureOutlined } from "@ant-design/icons"
import type { WorkspaceItemData } from "../../api/workspaces"

const { Text } = Typography

interface ArtifactListProps {
  items: WorkspaceItemData[]
  loading?: boolean
  onView: (item: WorkspaceItemData) => void
  onDelete: (itemId: string) => void
}

const typeIcon = (t: string) => {
  switch (t) {
    case "text": return <FileTextOutlined />
    case "markdown": return <FileTextOutlined />
    case "json":
    case "dict": return <CodeOutlined />
    case "list": return <UnorderedListOutlined />
    case "image_url": return <PictureOutlined />
    default: return <FileTextOutlined />
  }
}

const typeColor = (t: string) => {
  switch (t) {
    case "text": return "blue"
    case "markdown": return "purple"
    case "json":
    case "dict": return "green"
    case "list": return "orange"
    case "image_url": return "magenta"
    case "url": return "cyan"
    default: return "default"
  }
}

export default function ArtifactList({ items, loading, onView, onDelete }: ArtifactListProps) {
  if (!items || items.length === 0) {
    return <Empty description="暂无产物" />
  }

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: WorkspaceItemData) => (
        <Space>
          {typeIcon(record.type)}
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      render: (t: string) => <Tag color={typeColor(t)}>{t}</Tag>,
    },
    {
      title: "Agent",
      key: "agent",
      width: 120,
      render: (_: unknown, record: WorkspaceItemData) => {
        const agent = (record.metadata?.created_by as string) || record.owner
        return <Tag color="blue">{agent}</Tag>
      },
    },
    {
      title: "步骤",
      key: "step",
      width: 100,
      render: (_: unknown, record: WorkspaceItemData) => {
        const step = record.metadata?.step_id as string | undefined
        return step ? <Tag color="green">{step}</Tag> : <Text type="secondary">-</Text>
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: WorkspaceItemData) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => onView(record)}>查看</Button>
          <Popconfirm title="确定删除该产物？" onConfirm={() => onDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Table
      dataSource={items}
      columns={columns}
      rowKey="id"
      size="small"
      loading={loading}
      pagination={{ pageSize: 20 }}
    />
  )
}