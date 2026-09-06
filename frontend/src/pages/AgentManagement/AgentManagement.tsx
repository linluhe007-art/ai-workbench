import React, { useState } from "react"
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Spin,
  Alert,
  Modal,
  Input,
  Select,
  message,
  Badge,
} from "antd"
import {
  PlusOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  HeartOutlined,
  ReloadOutlined,
} from "@ant-design/icons"
import {
  useAgentRegistry,
  useRegisterAgent,
  useHeartbeat,
  useDisableAgent,
  useEnableAgent,
} from "../../hooks/useAgentLifecycle"

const { Title } = Typography

const stateColorMap: Record<string, string> = {
  idle: "default",
  running: "processing",
  waiting: "warning",
  completed: "success",
  failed: "error",
  ready: "success",
  initializing: "processing",
  stopped: "default",
  unknown: "default",
}

const AgentManagement: React.FC = () => {
  const { data, isLoading, error, refetch } = useAgentRegistry()
  const registerMut = useRegisterAgent()
  const heartbeatMut = useHeartbeat()
  const disableMut = useDisableAgent()
  const enableMut = useEnableAgent()

  const [modalOpen, setModalOpen] = useState(false)
  const [newAgentId, setNewAgentId] = useState("")
  const [newCaps, setNewCaps] = useState<string[]>([])

  const handleRegister = async () => {
    if (!newAgentId.trim()) return
    try {
      await registerMut.mutateAsync({ agentId: newAgentId.trim(), capabilities: newCaps })
      message.success("Agent 注册成功")
      setModalOpen(false)
      setNewAgentId("")
      setNewCaps([])
    } catch {
      message.error("注册失败")
    }
  }

  const handleHeartbeat = async (agentId: string) => {
    try {
      await heartbeatMut.mutateAsync(agentId)
      message.success("心跳已发送")
    } catch {
      message.error("心跳失败")
    }
  }

  const handleToggle = async (agentId: string, currentlyEnabled: boolean) => {
    try {
      if (currentlyEnabled) {
        await disableMut.mutateAsync(agentId)
        message.success("Agent 已禁用")
      } else {
        await enableMut.mutateAsync(agentId)
        message.success("Agent 已启用")
      }
    } catch {
      message.error("操作失败")
    }
  }

  const columns = [
    {
      title: "Agent",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: { agent_id: string }) => (
        <Space>
          <Badge status={record.enabled ? "processing" : "default"} />
          <span>{name || record.agent_id}</span>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "lifecycle_state",
      key: "state",
      render: (state: string) => <Tag color={stateColorMap[state] || "default"}>{state}</Tag>,
    },
    {
      title: "能力",
      dataIndex: "capabilities",
      key: "capabilities",
      render: (caps: string[]) => (
        <Space size={4} wrap>
          {caps.map((c) => (
            <Tag key={c} color="blue">{c}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "负载",
      key: "load",
      render: (_: unknown, record: { active_tasks: number; max_concurrent: number }) =>
        record.active_tasks + "/" + record.max_concurrent,
    },
    {
      title: "心跳",
      dataIndex: "last_heartbeat",
      key: "heartbeat",
      render: (hb: string | null) => (hb ? new Date(hb).toLocaleTimeString() : "从未"),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: { agent_id: string; enabled: boolean }) => (
        <Space>
          <Button
            size="small"
            icon={<HeartOutlined />}
            onClick={() => handleHeartbeat(record.agent_id)}
          >
            Beat
          </Button>
          <Button
            size="small"
            icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggle(record.agent_id, record.enabled)}
          >
            {record.enabled ? "禁用" : "启用"}
          </Button>
        </Space>
      ),
    },
  ]

  if (isLoading)
    return (
      <div style={{ padding: 48, textAlign: "center" }}>
        <Spin size="large" />
        <p>正在加载 Agent...</p>
      </div>
    )

  if (error)
    return <Alert type="error" message="加载失败" description={String(error)} />

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16, justifyContent: "space-between", width: "100%" }}>
        <Title level={3} style={{ margin: 0 }}>
          Agent Management
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Register
          </Button>
        </Space>
      </Space>

      <Card>
        <Table
          dataSource={data?.agents || []}
          columns={columns}
          rowKey="agent_id"
          pagination={false}
          size="middle"
          locale={{ emptyText: "暂无已注册 Agent" }}
        />
      </Card>

      <Modal
        title="注册 Agent"
        open={modalOpen}
        onOk={handleRegister}
        onCancel={() => setModalOpen(false)}
        confirmLoading={registerMut.isPending}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input
            placeholder="Agent ID"
            value={newAgentId}
            onChange={(e) => setNewAgentId(e.target.value)}
          />
          <Select
            mode="tags"
            placeholder="能力列表（逗号分隔）"
            style={{ width: "100%" }}
            value={newCaps}
            onChange={setNewCaps}
            tokenSeparators={[","]}
          />
        </Space>
      </Modal>
    </div>
  )
}

export default AgentManagement