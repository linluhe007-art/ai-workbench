import React, { useState } from "react"
import {
  Card,
  Typography,
  Tabs,
  Table,
  Tag,
  Button,
  Input,
  Select,
  Space,
  Modal,
  Form,
  Slider,
  Popconfirm,
  Spin,
  Alert,
  Empty,
  Descriptions,
} from "antd"
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  EditOutlined,
  BulbOutlined,
  ReloadOutlined,
} from "@ant-design/icons"
import {
  useMemorySearch,
  useMemoryStats,
  useMemoryByType,
  useSaveMemory,
  useUpdateMemory,
  useDeleteMemory,
  useProfile,
  usePreferences,
} from "../../hooks/useMemory"
import { MEMORY_TYPES, type MemoryItem, type SearchMemoryRequest } from "../../api/memory"

const { Title, Text, Paragraph } = Typography
const { Option } = Select

const TYPE_COLORS: Record<string, string> = {
  profile: "purple",
  preference: "orange",
  project: "blue",
  knowledge: "green",
  experience: "cyan",
}

const getTypeColor = (t: string) => TYPE_COLORS[t] || "default"

// ── Memory Explorer Main Component ──

const MemoryExplorer: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useMemoryStats()
  const { data: profile, isLoading: profileLoading } = useProfile()
  const { data: preferences, isLoading: prefsLoading } = usePreferences()
  const saveMut = useSaveMemory()
  const deleteMut = useDeleteMemory()
  const updateMut = useUpdateMemory()

  const [searchParams, setSearchParams] = useState<SearchMemoryRequest>({ query: "" })
  const [activeSearchParams, setActiveSearchParams] = useState<SearchMemoryRequest>({ query: "" })
  const { data: searchResults, isLoading: searchLoading, refetch } = useMemorySearch(activeSearchParams)

  const [addModalOpen, setAddModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<MemoryItem | null>(null)
  const [addForm] = Form.useForm()
  const [editForm] = Form.useForm()

  const [detailItem, setDetailItem] = useState<MemoryItem | null>(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)

  const handleSearch = () => {
    setActiveSearchParams({ ...searchParams })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch()
  }

  const handleAdd = async () => {
    const values = await addForm.validateFields()
    saveMut.mutate(values)
    setAddModalOpen(false)
    addForm.resetFields()
  }

  const handleEdit = async () => {
    if (!editingItem) return
    const values = await editForm.validateFields()
    updateMut.mutate({ id: editingItem.id, data: values })
    setEditModalOpen(false)
    setEditingItem(null)
    editForm.resetFields()
  }

  const handleDelete = (id: string) => deleteMut.mutate(id)

  const openEdit = (item: MemoryItem) => {
    setEditingItem(item)
    editForm.setFieldsValue({
      content: item.content,
      memory_type: item.memory_type,
      importance: item.importance,
      tags: item.tags,
    })
    setEditModalOpen(true)
  }

  const columns = [
    { title: "内容", dataIndex: "content", key: "content", ellipsis: true, render: (text: string) => <Text>{text.length > 80 ? text.slice(0, 80) + "..." : text}</Text> },
    { title: "类型", dataIndex: "memory_type", key: "type", width: 110, render: (t: string) => <Tag color={getTypeColor(t)}>{t}</Tag> },
    { title: "重要度", dataIndex: "importance", key: "importance", width: 110, render: (v: number) => (v * 100).toFixed(0) + "%" },
    { title: "标签", dataIndex: "tags", key: "tags", width: 200, render: (tags: string[]) => tags?.map((t: string) => <Tag key={t}>{t}</Tag>) || null },
    {
      title: "操作", key: "actions", width: 160,
      render: (_: unknown, record: MemoryItem) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确定删除该记忆？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const results = searchResults?.results || []

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={2}><BulbOutlined /> Memory Explorer</Title>
      <Paragraph type="secondary">Your personal long-term memory. Profiles, preferences, projects, knowledge, and experiences.</Paragraph>

      <Tabs defaultActiveKey="all" items={[
        {
          key: "all",
          label: "全部记忆",
          children: (
            <>
              {/* Stats Row */}
              {!statsLoading && stats?.data && (
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap>
                    {Object.entries(stats.data.by_type).map(([type, count]) => (
                      <Tag key={type} color={getTypeColor(type)}>{type}: {count}</Tag>
                    ))}
                    <Text type="secondary">Total: {stats.data.total_memories}</Text>
                  </Space>
                </Card>
              )}

              {/* Search Bar */}
              <Space style={{ marginBottom: 16, width: "100%" }} wrap>
                <Input
                  placeholder="搜索记忆..."
                  prefix={<SearchOutlined />}
                  value={searchParams.query || ""}
                  onChange={(e) => setSearchParams((p) => ({ ...p, query: e.target.value }))}
                  onKeyDown={handleKeyDown}
                  style={{ width: 280 }}
                />
                <Select
                  placeholder="类型"
                  allowClear
                  style={{ width: 140 }}
                  value={searchParams.memory_type}
                  onChange={(v) => setSearchParams((p) => ({ ...p, memory_type: v }))}
                >
                  {MEMORY_TYPES.map((t) => <Option key={t} value={t}>{t}</Option>)}
                </Select>
                <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
                <Button icon={<ReloadOutlined />} onClick={() => { setSearchParams({ query: "" }); setActiveSearchParams({ query: "" }); }}>清空</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>新增记忆</Button>
              </Space>

              {/* Results */}
              {searchLoading ? <Spin /> : (
                results.length === 0 ? (
                  <Empty description="未找到记忆，请先新增一条！" />
                ) : (
                  <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={results}
                    size="middle"
                    onRow={(record) => ({
                      onClick: () => { setDetailItem(record); setDetailModalOpen(true) },
                      style: { cursor: "pointer" },
                    })}
                    pagination={{ pageSize: 15 }}
                  />
                )
              )}
            </>
          ),
        },
        {
          key: "profile",
          label: "个人资料",
          children: <MemoryTypeList type="profile" loading={profileLoading} data={profile?.results || []} />,
        },
        {
          key: "preferences",
          label: "偏好设置",
          children: <MemoryTypeList type="preference" loading={prefsLoading} data={preferences?.results || []} />,
        },
      ]} />

      {/* Add Modal */}
      <Modal title="新增记忆" open={addModalOpen} onOk={handleAdd} onCancel={() => { setAddModalOpen(false); addForm.resetFields() }} confirmLoading={saveMut.isPending}>
        <Form form={addForm} layout="vertical" initialValues={{ memory_type: "knowledge", importance: 0.5, tags: [] }}>
          <Form.Item name="content" label="内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="memory_type" label="类型">
            <Select>{MEMORY_TYPES.map((t) => <Option key={t} value={t}>{t}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="importance" label="重要度">
            <Slider min={0} max={1} step={0.1} marks={{ 0: "0", 0.5: "0.5", 1: "1" }} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="添加标签" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal title="编辑记忆" open={editModalOpen} onOk={handleEdit} onCancel={() => { setEditModalOpen(false); setEditingItem(null) }} confirmLoading={updateMut.isPending}>
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="memory_type" label="类型">
            <Select>{MEMORY_TYPES.map((t) => <Option key={t} value={t}>{t}</Option>)}</Select>
          </Form.Item>
          <Form.Item name="importance" label="重要度">
            <Slider min={0} max={1} step={0.1} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal title="记忆详情" open={detailModalOpen} onCancel={() => setDetailModalOpen(false)} footer={null} width={600}>
        {detailItem && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{detailItem.id}</Descriptions.Item>
            <Descriptions.Item label="类型"><Tag color={getTypeColor(detailItem.memory_type)}>{detailItem.memory_type}</Tag></Descriptions.Item>
            <Descriptions.Item label="内容"><Paragraph style={{ whiteSpace: "pre-wrap" }}>{detailItem.content}</Paragraph></Descriptions.Item>
            <Descriptions.Item label="重要度">{(detailItem.importance * 100).toFixed(0)}%</Descriptions.Item>
            <Descriptions.Item label="标签">{detailItem.tags?.map((t) => <Tag key={t}>{t}</Tag>) || "None"}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{detailItem.created_at}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{detailItem.updated_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

// ── Memory Type List Sub-component ──

const MemoryTypeList: React.FC<{ type: string; loading: boolean; data: MemoryItem[] }> = ({ type, loading, data }) => {
  const deleteMut = useDeleteMemory()
  return loading ? <Spin /> : data.length === 0 ? <Empty description={"No " + type + " memories"} /> : (
    <Table rowKey="id" dataSource={data} columns={[
      { title: "内容", dataIndex: "content", ellipsis: true },
      { title: "重要度", dataIndex: "importance", width: 110, render: (v: number) => (v * 100).toFixed(0) + "%" },
      { title: "标签", dataIndex: "tags", width: 200, render: (tags: string[]) => tags?.map((t: string) => <Tag key={t}>{t}</Tag>) },
      { title: "创建时间", dataIndex: "created_at", width: 180, render: (d: string) => d?.slice(0, 19) },
      {
        title: "", key: "del", width: 60,
        render: (_: unknown, r: MemoryItem) => <Popconfirm title="确定删除？" onConfirm={() => deleteMut.mutate(r.id)}><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm>
      },
    ]} size="middle" pagination={{ pageSize: 15 }} />
  )
}

export default MemoryExplorer

