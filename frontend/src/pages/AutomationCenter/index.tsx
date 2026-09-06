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
  Tooltip,
  Drawer,
  Descriptions,
} from "antd"
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  ReloadOutlined,
  HistoryOutlined,
} from "@ant-design/icons"
import {
  useAutomations,
  useCreateAutomation,
  useRunAutomation,
  useUpdateAutomationStatus,
  useDeleteAutomation,
  useAutomationLogs,
} from "../../hooks/useAutomation"

const { Title } = Typography

const statusColorMap: Record<string, string> = {
  active: "green",
  paused: "orange",
  disabled: "red",
  completed: "blue",
}

const statusLabelMap: Record<string, string> = {
  active: "\u6fc0\u6d3b",
  paused: "\u6682\u505c",
  disabled: "\u7981\u7528",
  completed: "\u5df2\u5b8c\u6210",
}

const triggerTypeLabelMap: Record<string, string> = {
  schedule: "\u5b9a\u65f6",
  event: "\u4e8b\u4ef6",
  manual: "\u624b\u52a8",
  webhook: "Webhook",
}

const AutomationCenter: React.FC = () => {
  const { data, isLoading, error, refetch } = useAutomations()
  const createMut = useCreateAutomation()
  const runMut = useRunAutomation()
  const statusMut = useUpdateAutomationStatus()
  const deleteMut = useDeleteAutomation()

  const [modalOpen, setModalOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDesc, setNewDesc] = useState("")
  const [newTriggerType, setNewTriggerType] = useState("schedule")
  const [newCron, setNewCron] = useState("")
  const [newActionType, setNewActionType] = useState("create_task")

  const [logsDrawerOpen, setLogsDrawerOpen] = useState(false)
  const [selectedAutoId, setSelectedAutoId] = useState<string | null>(null)
  const { data: logsData } = useAutomationLogs(selectedAutoId)

  const automations = data?.automations || []

  const handleCreate = async () => {
    if (!newName.trim()) {
      message.warning("\u8bf7\u8f93\u5165\u81ea\u52a8\u5316\u540d\u79f0")
      return
    }
    try {
      await createMut.mutateAsync({
        name: newName.trim(),
        description: newDesc.trim(),
        trigger_type: newTriggerType,
        cron_expression: newCron.trim(),
        action_type: newActionType,
      })
      message.success("\u521b\u5efa\u6210\u529f")
      setModalOpen(false)
      setNewName("")
      setNewDesc("")
      setNewTriggerType("schedule")
      setNewCron("")
    } catch {
      message.error("\u521b\u5efa\u5931\u8d25")
    }
  }

  const handleRun = async (id: string) => {
    try {
      await runMut.mutateAsync(id)
      message.success("\u6267\u884c\u6210\u529f")
    } catch {
      message.error("\u6267\u884c\u5931\u8d25")
    }
  }

  const handleToggleStatus = async (id: string, currentStatus: string) => {
    const next = currentStatus === "active" ? "paused" : "active"
    try {
      await statusMut.mutateAsync({ id, status: next })
      message.success("\u72b6\u6001\u66f4\u65b0\u6210\u529f")
    } catch {
      message.error("\u72b6\u6001\u66f4\u65b0\u5931\u8d25")
    }
  }

  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: "\u786e\u8ba4\u5220\u9664",
      content: "\u5220\u9664\u540e\u65e0\u6cd5\u6062\u590d\uff0c\u786e\u5b9a\u7ee7\u7eed\uff1f",
      okText: "\u5220\u9664",
      okType: "danger",
      cancelText: "\u53d6\u6d88",
      onOk: async () => {
        try {
          await deleteMut.mutateAsync(id)
          message.success("\u5220\u9664\u6210\u529f")
        } catch {
          message.error("\u5220\u9664\u5931\u8d25")
        }
      },
    })
  }

  const columns = [
    {
      title: "\u540d\u79f0",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: Record<string, unknown>) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.description ? (
            <Tooltip title={record.description as string}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {(record.description as string).slice(0, 30)}
                {(record.description as string).length > 30 ? "..." : ""}
              </Typography.Text>
            </Tooltip>
          ) : null}
        </Space>
      ),
    },
    {
      title: "\u89e6\u53d1\u7c7b\u578b",
      dataIndex: "trigger",
      key: "trigger_type",
      width: 100,
      render: (trigger: Record<string, unknown>) => (
        <Tag>{triggerTypeLabelMap[trigger.trigger_type as string] || (trigger.trigger_type as string)}</Tag>
      ),
    },
    {
      title: "Cron",
      dataIndex: "trigger",
      key: "cron",
      width: 140,
      render: (trigger: Record<string, unknown>) =>
        trigger.cron_expression ? (
          <code style={{ fontSize: 12 }}>{trigger.cron_expression as string}</code>
        ) : (
          <span style={{ color: "#ccc" }}>-</span>
        ),
    },
    {
      title: "\u72b6\u6001",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (status: string) => (
        <Tag color={statusColorMap[status] || "default"}>
          {statusLabelMap[status] || status}
        </Tag>
      ),
    },
    {
      title: "\u4e0a\u6b21\u6267\u884c",
      dataIndex: "last_run_at",
      key: "last_run_at",
      width: 170,
      render: (v: string) =>
        v ? new Date(v).toLocaleString("zh-CN") : <span style={{ color: "#ccc" }}>-</span>,
    },
    {
      title: "\u6267\u884c\u6b21\u6570",
      dataIndex: "run_count",
      key: "run_count",
      width: 80,
    },
    {
      title: "\u64cd\u4f5c",
      key: "actions",
      width: 240,
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record.id as string)}
            loading={runMut.isPending}
          >
            \u8fd0\u884c
          </Button>
          <Button
            size="small"
            icon={record.status === "active" ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleStatus(record.id as string, record.status as string)}
          >
            {record.status === "active" ? "\u6682\u505c" : "\u6fc0\u6d3b"}
          </Button>
          <Button
            size="small"
            icon={<HistoryOutlined />}
            onClick={() => {
              setSelectedAutoId(record.id as string)
              setLogsDrawerOpen(true)
            }}
          >
            \u65e5\u5fd7
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id as string)}
          />
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          \u81ea\u52a8\u5316\u4e2d\u5fc3
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            \u5237\u65b0
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            \u65b0\u5efa\u81ea\u52a8\u5316
          </Button>
        </Space>
      </div>

      <Card>
        {error ? (
          <Alert type="error" message="\u52a0\u8f7d\u5931\u8d25" description={String(error)} showIcon />
        ) : (
          <Table
            columns={columns}
            dataSource={automations}
            rowKey="id"
            loading={isLoading}
            pagination={{ pageSize: 20 }}
            locale={{ emptyText: "\u6682\u65e0\u81ea\u52a8\u5316\u4efb\u52a1\uff0c\u70b9\u51fb\u201c\u65b0\u5efa\u81ea\u52a8\u5316\u201d\u5f00\u59cb" }}
          />
        )}
      </Card>

      <Modal
        title="\u65b0\u5efa\u81ea\u52a8\u5316"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending}
        okText="\u521b\u5efa"
        cancelText="\u53d6\u6d88"
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <div style={{ marginBottom: 4 }}>\u540d\u79f0 *</div>
            <Input
              placeholder="\u4f8b\u5982\uff1a\u6bcf\u65e5\u62a5\u544a\u751f\u6210"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>\u63cf\u8ff0</div>
            <Input.TextArea
              placeholder="\u53ef\u9009\u63cf\u8ff0"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              rows={2}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>\u89e6\u53d1\u7c7b\u578b</div>
            <Select
              value={newTriggerType}
              onChange={setNewTriggerType}
              style={{ width: "100%" }}
              options={[
                { value: "schedule", label: "\u5b9a\u65f6 (Cron)" },
                { value: "manual", label: "\u624b\u52a8\u89e6\u53d1" },
                { value: "event", label: "\u4e8b\u4ef6\u89e6\u53d1" },
                { value: "webhook", label: "Webhook" },
              ]}
            />
          </div>
          {newTriggerType === "schedule" && (
            <div>
              <div style={{ marginBottom: 4 }}>Cron \u8868\u8fbe\u5f0f</div>
              <Input
                placeholder="\u4f8b\u5982\uff1a0 18 * * * (\u6bcf\u592918:00)"
                value={newCron}
                onChange={(e) => setNewCron(e.target.value)}
              />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                \u5206 \u65f6 \u65e5 \u6708 \u5468
              </Typography.Text>
            </div>
          )}
          <div>
            <div style={{ marginBottom: 4 }}>\u52a8\u4f5c\u7c7b\u578b</div>
            <Select
              value={newActionType}
              onChange={setNewActionType}
              style={{ width: "100%" }}
              options={[
                { value: "create_task", label: "\u521b\u5efa\u4efb\u52a1" },
                { value: "notify", label: "\u53d1\u9001\u901a\u77e5" },
                { value: "export", label: "\u5bfc\u51fa\u6570\u636e" },
              ]}
            />
          </div>
        </Space>
      </Modal>

      <Drawer
        title="\u6267\u884c\u65e5\u5fd7"
        open={logsDrawerOpen}
        onClose={() => {
          setLogsDrawerOpen(false)
          setSelectedAutoId(null)
        }}
        width={600}
      >
        {logsData?.logs?.length ? (
          logsData.logs.map((log: Record<string, unknown>) => (
            <Card
              key={log.id as string}
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Space>
                  <Tag color={log.status === "completed" ? "green" : log.status === "failed" ? "red" : "blue"}>
                    {log.status as string}
                  </Tag>
                  <span style={{ fontSize: 12, color: "#999" }}>
                    {(log.created_at as string)?.slice(0, 19).replace("T", " ")}
                  </span>
                </Space>
              }
            >
              {log.error ? (
                <Alert type="error" message={log.error as string} />
              ) : (
                <Descriptions size="small" column={1}>
                  {Object.entries(log.result as Record<string, unknown> || {}).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k}>
                      {String(v).slice(0, 200)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              )}
            </Card>
          ))
        ) : (
          <Alert type="info" message="\u6682\u65e0\u6267\u884c\u65e5\u5fd7" />
        )}
      </Drawer>
    </div>
  )
}

export default AutomationCenter
