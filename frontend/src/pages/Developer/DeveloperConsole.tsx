import React, { useState } from "react"
import {
  Card, Table, Button, Space, Typography, Spin, Alert, Modal,
  Input, Select, Tag, message, Tabs, Statistic, Row, Col, CopyToClipboard,
} from "antd"
import { PlusOutlined, DeleteOutlined, KeyOutlined, LinkOutlined, CopyOutlined } from "@ant-design/icons"
import {
  useAPIKeys, useCreateAPIKey, useDeleteAPIKey,
  useWebhooks, useCreateWebhook, useDeleteWebhook,
} from "../../hooks/useDeveloper"

const { Title, Text } = Typography

const DeveloperConsole: React.FC = () => {
  // API Keys
  const { data: keysData, isLoading: keysLoading } = useAPIKeys()
  const createKeyMut = useCreateAPIKey()
  const deleteKeyMut = useDeleteAPIKey()

  const [keyModalOpen, setKeyModalOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState("")
  const [newKeyPerms, setNewKeyPerms] = useState<string[]>(["read"])
  const [createdRawKey, setCreatedRawKey] = useState("")

  // Webhooks
  const { data: whData, isLoading: whLoading } = useWebhooks()
  const createWhMut = useCreateWebhook()
  const deleteWhMut = useDeleteWebhook()

  const [whModalOpen, setWhModalOpen] = useState(false)
  const [newWhUrl, setNewWhUrl] = useState("")
  const [newWhEvents, setNewWhEvents] = useState<string[]>(["task.completed"])

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return
    try {
      const res = await createKeyMut.mutateAsync({ name: newKeyName.trim(), permissions: newKeyPerms })
      setCreatedRawKey(res.raw_key)
      message.success("API Key 创建成功")
    } catch { message.error("创建 API Key 失败") }
  }

  const handleCreateWebhook = async () => {
    if (!newWhUrl.trim()) return
    try {
      await createWhMut.mutateAsync({ url: newWhUrl.trim(), events: newWhEvents })
      message.success("Webhook 创建成功")
      setWhModalOpen(false)
      setNewWhUrl("")
    } catch { message.error("创建 Webhook 失败") }
  }

  const handleDeleteKey = async (id: string) => {
    try { await deleteKeyMut.mutateAsync(id); message.success("Key 已删除") }
    catch { message.error("删除失败") }
  }

  const handleDeleteWebhook = async (id: string) => {
    try { await deleteWhMut.mutateAsync(id); message.success("Webhook 已删除") }
    catch { message.error("删除失败") }
  }

  const keyColumns = [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "前缀", dataIndex: "key_prefix", key: "prefix", render: (v: string) => <Text code>{v}</Text> },
    { title: "权限", dataIndex: "permissions", key: "perms", render: (p: string[]) => <Space size={4}>{p.map((x) => <Tag key={x}>{x}</Tag>)}</Space> },
    { title: "状态", dataIndex: "enabled", key: "status", render: (e: boolean) => e ? <Tag color="green">已启用</Tag> : <Tag color="red">已吊销</Tag> },
    { title: "创建时间", dataIndex: "created_at", key: "created", render: (t: string) => t ? new Date(t).toLocaleString() : "-" },
    { title: "操作", key: "actions", render: (_: unknown, r: { id: string }) => <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteKey(r.id)}>删除</Button> },
  ]

  const whColumns = [
    { title: "URL", dataIndex: "url", key: "url", render: (u: string) => <Text code style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", display: "inline-block" }}>{u}</Text> },
    { title: "事件", dataIndex: "events", key: "events", render: (e: string[]) => <Space size={4}>{e.map((x) => <Tag key={x}>{x}</Tag>)}</Space> },
    { title: "已投递", dataIndex: "delivery_count", key: "delivered" },
    { title: "失败", dataIndex: "failure_count", key: "failed" },
    { title: "创建时间", dataIndex: "created_at", key: "created", render: (t: string) => t ? new Date(t).toLocaleString() : "-" },
    { title: "操作", key: "actions", render: (_: unknown, r: { id: string }) => <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteWebhook(r.id)}>删除</Button> },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>开发者控制台</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={8}><Card><Statistic title="API Key 数量" value={keysData?.total ?? 0} prefix={<KeyOutlined />} /></Card></Col>
        <Col span={8}><Card><Statistic title="Webhook 数量" value={whData?.total ?? 0} prefix={<LinkOutlined />} /></Card></Col>
        <Col span={8}><Card><Statistic title="Webhook 失败数" value={whData?.webhooks?.reduce((s: number, w: { failure_count: number }) => s + w.failure_count, 0) ?? 0} /></Card></Col>
      </Row>

      <Tabs defaultActiveKey="keys" items={[{
        key: "keys", label: "API Key",
        children: (
          <>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { setKeyModalOpen(true); setCreatedRawKey(""); }} style={{ marginBottom: 16 }}>创建 API Key</Button>
            {keysLoading ? <Spin /> : (
              <Table dataSource={keysData?.api_keys || []} columns={keyColumns} rowKey="id" pagination={false} size="middle" locale={{ emptyText: "暂无 API Key" }} />
            )}
            <Modal title="创建 API Key" open={keyModalOpen} onOk={handleCreateKey} onCancel={() => setKeyModalOpen(false)} confirmLoading={createKeyMut.isPending}>
              <Space direction="vertical" style={{ width: "100%" }}>
                <Input placeholder="密钥名称" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} />
                <Select mode="tags" placeholder="权限" value={newKeyPerms} onChange={setNewKeyPerms} style={{ width: "100%" }} />
                {createdRawKey && (
                  <Alert type="success" message={
                    <Space><Text copyable>{createdRawKey}</Text><Text type="danger">Save this key now - it won't be shown again!</Text></Space>
                  } />
                )}
              </Space>
            </Modal>
          </>
        ),
      }, {
        key: "webhooks", label: "Webhook",
        children: (
          <>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setWhModalOpen(true)} style={{ marginBottom: 16 }}>新增 Webhook</Button>
            {whLoading ? <Spin /> : (
              <Table dataSource={whData?.webhooks || []} columns={whColumns} rowKey="id" pagination={false} size="middle" locale={{ emptyText: "暂无 Webhook" }} />
            )}
            <Modal title="新增 Webhook" open={whModalOpen} onOk={handleCreateWebhook} onCancel={() => setWhModalOpen(false)} confirmLoading={createWhMut.isPending}>
              <Space direction="vertical" style={{ width: "100%" }}>
                <Input placeholder="Webhook URL" value={newWhUrl} onChange={(e) => setNewWhUrl(e.target.value)} />
                <Select mode="tags" placeholder="事件" value={newWhEvents} onChange={setNewWhEvents} style={{ width: "100%" }} options={[
                  { label: "task.completed", value: "task.completed" },
                  { label: "task.failed", value: "task.failed" },
                  { label: "artifact.created", value: "artifact.created" },
                  { label: "agent.failed", value: "agent.failed" },
                ]} />
              </Space>
            </Modal>
          </>
        ),
      }]} />
    </div>
  )
}

export default DeveloperConsole