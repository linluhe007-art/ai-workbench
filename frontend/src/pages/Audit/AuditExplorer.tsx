import { useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Table,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  Button,
  Card,
  Descriptions,
  Modal,
  Alert,
  Spin,
  Empty,
} from 'antd'
import {
  SearchOutlined,
  ClearOutlined,
  AuditOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useAuditRecords, useAuditStats } from '../../hooks/useAudit'
import type { AuditRecord, AuditQueryParams } from '../../api/audit'

const { Title } = Typography

const ACTION_COLORS: Record<string, string> = {
  create_task: 'blue',
  task_started: 'green',
  task_completed: 'green',
  task_failed: 'red',
  task_cancelled: 'orange',
  task_paused: 'gold',
  task_resumed: 'cyan',
  task_retry: 'purple',
  task_timeout: 'volcano',
  step_started: 'geekblue',
  step_completed: 'green',
  artifact_created: 'lime',
}

const RESOURCE_COLORS: Record<string, string> = {
  task: 'blue',
  agent: 'purple',
  artifact: 'green',
  workspace: 'cyan',
  execution: 'orange',
}

const ACTION_OPTIONS = [
  { value: 'create_task', label: '创建任务' },
  { value: 'task_started', label: '任务启动' },
  { value: 'task_completed', label: '任务完成' },
  { value: 'task_failed', label: '任务失败' },
  { value: 'task_cancelled', label: '任务取消' },
  { value: 'task_paused', label: '任务暂停' },
  { value: 'task_resumed', label: '任务恢复' },
  { value: 'task_retry', label: '任务重试' },
  { value: 'task_timeout', label: '任务超时' },
  { value: 'step_started', label: '步骤开始' },
  { value: 'step_completed', label: '步骤完成' },
  { value: 'artifact_created', label: '产物创建' },
]

const RESOURCE_TYPE_OPTIONS = [
  { value: 'task', label: '任务' },
  { value: 'agent', label: 'Agent' },
  { value: 'artifact', label: '产物' },
  { value: 'workspace', label: '工作空间' },
  { value: 'execution', label: '执行' },
]

export default function AuditExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [detailModal, setDetailModal] = useState<AuditRecord | null>(null)

  const [params, setParams] = useState<AuditQueryParams>({
    task_id: searchParams.get('task_id') || null,
    actor: searchParams.get('actor') || null,
    action: searchParams.get('action') || null,
    resource_type: searchParams.get('resource_type') || null,
    resource_id: searchParams.get('resource_id') || null,
    limit: 50,
    offset: 0,
  })

  const { data, isLoading, isError, error, refetch } = useAuditRecords(params)
  const { data: stats } = useAuditStats()

  const handleSearch = useCallback(() => {
    refetch()
  }, [refetch])

  const handleClear = useCallback(() => {
    const cleared: AuditQueryParams = { limit: 50, offset: 0 }
    setParams(cleared)
    setSearchParams({})
  }, [setSearchParams])

  const handleFilterChange = useCallback(
    (key: keyof AuditQueryParams, value: string | null) => {
      setParams((prev) => {
        const next = { ...prev, [key]: value || undefined, offset: 0 }
        const newSearchParams = new URLSearchParams()
        if (next.task_id) newSearchParams.set('task_id', next.task_id)
        if (next.actor) newSearchParams.set('actor', next.actor)
        if (next.action) newSearchParams.set('action', next.action)
        if (next.resource_type) newSearchParams.set('resource_type', next.resource_type)
        setSearchParams(newSearchParams)
        return next
      })
    },
    [setSearchParams],
  )

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (ts: string) => new Date(ts).toLocaleString(),
    },
    {
      title: '操作者',
      dataIndex: 'actor',
      key: 'actor',
      width: 120,
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      width: 160,
      render: (action: string) => (
        <Tag color={ACTION_COLORS[action] || 'default'}>{action}</Tag>
      ),
    },
    {
      title: '资源',
      key: 'resource',
      width: 200,
      render: (_: unknown, record: AuditRecord) => (
        <Space size={4}>
          <Tag color={RESOURCE_COLORS[record.resource_type] || 'default'}>
            {record.resource_type}
          </Tag>
          <Typography.Text code ellipsis style={{ maxWidth: 120 }}>
            {record.resource_id}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '任务',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      ellipsis: true,
      render: (taskId: string | null) =>
        taskId ? (
          <Typography.Text code ellipsis style={{ maxWidth: 180 }}>
            {taskId}
          </Typography.Text>
        ) : (
          '-'
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: AuditRecord) => (
        <Button size="small" type="link" onClick={() => setDetailModal(record)}>
          Detail
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>
        <AuditOutlined /> Audit Explorer
      </Title>

      {stats && (
        <Typography.Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
          Total audit records: {stats.total_records}
        </Typography.Text>
      )}

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="任务 ID"
            value={params.task_id || ''}
            onChange={(e) => handleFilterChange('task_id', e.target.value || null)}
            style={{ width: 200 }}
            allowClear
          />
          <Input
            placeholder="操作者"
            value={params.actor || ''}
            onChange={(e) => handleFilterChange('actor', e.target.value || null)}
            style={{ width: 140 }}
            allowClear
          />
          <Select
            placeholder="动作"
            value={params.action || undefined}
            onChange={(val) => handleFilterChange('action', val || null)}
            style={{ width: 170 }}
            allowClear
            showSearch
            options={ACTION_OPTIONS}
          />
          <Select
            placeholder="资源类型"
            value={params.resource_type || undefined}
            onChange={(val) => handleFilterChange('resource_type', val || null)}
            style={{ width: 150 }}
            allowClear
            options={RESOURCE_TYPE_OPTIONS}
          />
          <Input
            placeholder="资源 ID"
            value={params.resource_id || ''}
            onChange={(e) => handleFilterChange('resource_id', e.target.value || null)}
            style={{ width: 200 }}
            allowClear
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            Search
          </Button>
          <Button icon={<ClearOutlined />} onClick={handleClear}>
            Clear
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
        </Space>
      </Card>

      {/* Error */}
      {isError && (
        <Alert
          message="加载审计记录失败"
          description={error instanceof Error ? error.message : '未知错误'}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      )}

      {/* Loading */}
      {isLoading && <Spin tip="正在加载审计记录..." style={{ display: 'block', margin: '40px auto' }} />}

      {/* Empty */}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <Empty description="未找到审计记录" />
      )}

      {/* Table */}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <Table
          columns={columns}
          dataSource={data.items}
          rowKey="id"
          size="small"
          pagination={{
            current: (params.offset || 0) / (params.limit || 50) + 1,
            pageSize: params.limit || 50,
            total: data.total,
            showSizeChanger: true,
            showTotal: (total) => `Total: ${total}`,
            onChange: (page, pageSize) => {
              setParams((prev) => ({
                ...prev,
                limit: pageSize,
                offset: (page - 1) * pageSize,
              }))
            },
          }}
        />
      )}

      {/* Detail Modal */}
      <Modal
        title="审计记录详情"
        open={!!detailModal}
        onCancel={() => setDetailModal(null)}
        footer={<Button onClick={() => setDetailModal(null)}>关闭</Button>}
        width={700}
      >
        {detailModal && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="ID">{detailModal.id}</Descriptions.Item>
            <Descriptions.Item label="时间戳">
              {new Date(detailModal.timestamp).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="操作者">{detailModal.actor}</Descriptions.Item>
            <Descriptions.Item label="动作">
              <Tag color={ACTION_COLORS[detailModal.action] || 'default'}>
                {detailModal.action}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="资源类型">
              <Tag color={RESOURCE_COLORS[detailModal.resource_type] || 'default'}>
                {detailModal.resource_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="资源 ID">{detailModal.resource_id}</Descriptions.Item>
            <Descriptions.Item label="任务 ID">{detailModal.task_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="请求 ID">{detailModal.request_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="变更前" span={2}>
              <pre style={{ maxHeight: 150, overflow: 'auto', fontSize: 12 }}>
                {JSON.stringify(detailModal.before, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="变更后" span={2}>
              <pre style={{ maxHeight: 150, overflow: 'auto', fontSize: 12 }}>
                {JSON.stringify(detailModal.after, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="元数据" span={2}>
              <pre style={{ maxHeight: 150, overflow: 'auto', fontSize: 12 }}>
                {JSON.stringify(detailModal.metadata, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}