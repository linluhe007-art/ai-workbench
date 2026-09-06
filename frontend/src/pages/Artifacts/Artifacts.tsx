import { useState, useCallback, useEffect } from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { Card, Input, Button, Space, Table, Tag, Select, DatePicker, Typography, Spin, Alert, Modal, Row, Col } from "antd"
import { SearchOutlined, ClearOutlined, ReloadOutlined, EyeOutlined, FileSearchOutlined } from "@ant-design/icons"
import { useArtifactSearch } from "../../hooks/useArtifactSearch"
import type { ArtifactSearchParams } from "../../api/artifactSearch"
import type { ArtifactItem } from "../../api/artifacts"
import ArtifactViewer from "../../components/artifacts/ArtifactViewer"

const { Title } = Typography
const { RangePicker } = DatePicker

const typeOptions = ["text", "markdown", "json", "list", "url", "image_url"]
const typeColors: Record<string, string> = { text: "blue", markdown: "purple", json: "green", list: "orange", url: "cyan", image_url: "magenta" }

export default function ArtifactsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  // Initialize from URL params
  const [query, setQuery] = useState(searchParams.get("q") || "")
  const [typeFilter, setTypeFilter] = useState<string | undefined>(searchParams.get("type") || undefined)
  const [agentFilter, setAgentFilter] = useState(searchParams.get("agent_id") || "")
  const [taskFilter, setTaskFilter] = useState(searchParams.get("task_id") || "")
  const [workspaceFilter, setWorkspaceFilter] = useState(searchParams.get("workspace_id") || "")
  const [stepFilter, setStepFilter] = useState(searchParams.get("step_id") || "")
  const [sortBy, setSortBy] = useState<"created_at" | "name" | "type">((searchParams.get("sort_by") as "created_at" | "name" | "type") || "created_at")
  const [order, setOrder] = useState<"asc" | "desc">((searchParams.get("order") as "asc" | "desc") || "desc")
  const [page, setPage] = useState(parseInt(searchParams.get("page") || "1", 10))
  const pageSize = 20

  const [viewing, setViewing] = useState<ArtifactItem | null>(null)

  const buildParams = useCallback((): ArtifactSearchParams => ({
    q: query || undefined,
    type: typeFilter,
    agent_id: agentFilter || undefined,
    task_id: taskFilter || undefined,
    workspace_id: workspaceFilter || undefined,
    step_id: stepFilter || undefined,
    sort_by: sortBy,
    order,
    limit: pageSize,
    offset: (page - 1) * pageSize,
  }), [query, typeFilter, agentFilter, taskFilter, workspaceFilter, stepFilter, sortBy, order, page])

  const { data, isLoading, error, refetch } = useArtifactSearch(buildParams())

  // Sync URL params
  useEffect(() => {
    const p: Record<string, string> = {}
    if (query) p.q = query
    if (typeFilter) p.type = typeFilter
    if (agentFilter) p.agent_id = agentFilter
    if (taskFilter) p.task_id = taskFilter
    if (workspaceFilter) p.workspace_id = workspaceFilter
    if (stepFilter) p.step_id = stepFilter
    if (sortBy !== "created_at") p.sort_by = sortBy
    if (order !== "desc") p.order = order
    if (page > 1) p.page = String(page)
    setSearchParams(p, { replace: true })
  }, [query, typeFilter, agentFilter, taskFilter, workspaceFilter, stepFilter, sortBy, order, page, setSearchParams])

  const handleClear = () => {
    setQuery("")
    setTypeFilter(undefined)
    setAgentFilter("")
    setTaskFilter("")
    setWorkspaceFilter("")
    setStepFilter("")
    setSortBy("created_at")
    setOrder("desc")
    setPage(1)
  }

  const items = data?.items || []
  const total = data?.total || 0

  const columns = [
    { title: "名称", dataIndex: "name", key: "name", ellipsis: true, render: (n: string) => <span style={{ fontWeight: 500 }}>{n}</span> },
    { title: "类型", dataIndex: "type", key: "type", width: 100, render: (t: string) => <Tag color={typeColors[t] || "default"}>{t}</Tag> },
    { title: "Agent", key: "agent", width: 120, render: (_: unknown, r: ArtifactItem) => <Tag color="blue">{(r.metadata?.created_by as string) || r.owner}</Tag> },
    { title: "步骤", key: "step", width: 100, render: (_: unknown, r: ArtifactItem) => { const s = r.metadata?.step_id as string | undefined; return s ? <Tag color="green">{s}</Tag> : "-" } },
    { title: "任务", key: "task", width: 140, render: (_: unknown, r: ArtifactItem) => { const t = r.metadata?.task_id as string | undefined; return t ? <Tag style={{ cursor: "pointer" }} onClick={() => navigate(`/tasks/${t}`)}>{t.slice(0, 12)}...</Tag> : "-" } },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 170, render: (t: string) => new Date(t).toLocaleString("zh-CN") },
    { title: "操作", key: "action", width: 80, render: (_: unknown, r: ArtifactItem) => <Button size="small" icon={<EyeOutlined />} onClick={() => setViewing(r)} /> },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Title level={4}><FileSearchOutlined /> Artifact Explorer</Title>

      {/* Search + Filters */}
      <Card size="small">
        <Row gutter={[12, 12]}>
          <Col span={24}>
            <Space.Compact style={{ width: "100%" }}>
              <Input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1) }} placeholder="搜索产物..." allowClear onPressEnter={() => refetch()} />
              <Button type="primary" icon={<SearchOutlined />} onClick={() => refetch()}>搜索</Button>
              <Button icon={<ClearOutlined />} onClick={handleClear}>清空</Button>
            </Space.Compact>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select allowClear placeholder="类型" value={typeFilter} onChange={(v) => { setTypeFilter(v); setPage(1) }} style={{ width: "100%" }} options={typeOptions.map(t => ({ label: t, value: t }))} />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input placeholder="Agent ID" value={agentFilter} onChange={(e) => { setAgentFilter(e.target.value); setPage(1) }} allowClear />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input placeholder="任务 ID" value={taskFilter} onChange={(e) => { setTaskFilter(e.target.value); setPage(1) }} allowClear />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input placeholder="工作空间 ID" value={workspaceFilter} onChange={(e) => { setWorkspaceFilter(e.target.value); setPage(1) }} allowClear />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Input placeholder="步骤 ID" value={stepFilter} onChange={(e) => { setStepFilter(e.target.value); setPage(1) }} allowClear />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Space.Compact style={{ width: "100%" }}>
              <Select value={sortBy} onChange={setSortBy} style={{ width: "60%" }} options={[{ label: "创建时间", value: "created_at" }, { label: "名称", value: "name" }, { label: "类型", value: "type" }]} />
              <Select value={order} onChange={setOrder} style={{ width: "40%" }} options={[{ label: "降序", value: "desc" }, { label: "升序", value: "asc" }]} />
            </Space.Compact>
          </Col>
        </Row>
      </Card>

      {/* Error */}
      {error && <Alert message="搜索失败" description={error.message} type="error" showIcon action={<Button size="small" onClick={() => refetch()}>重试</Button>} />}

      {/* Results */}
      <Card size="small" title={`Results (${total})`}>
        {isLoading ? (
          <Spin style={{ display: "block", margin: "40px auto" }} />
        ) : (
          <Table
            dataSource={items}
            columns={columns}
            rowKey="id"
            size="small"
            pagination={{
              current: page,
              pageSize,
              total,
              onChange: (p) => setPage(p),
              showTotal: (t) => `Total ${t}`,
            }}
          />
        )}
      </Card>

      {/* Detail Modal */}
      <Modal title={viewing?.name || "详情"} open={!!viewing} onCancel={() => setViewing(null)} footer={null} width={640}>
        {viewing && <ArtifactViewer item={viewing} onClose={() => setViewing(null)} />}
      </Modal>
    </Space>
  )
}