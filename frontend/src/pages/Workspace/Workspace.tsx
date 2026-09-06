import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Button, Space, Spin, message, Row, Col, Statistic } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, FileOutlined, DatabaseOutlined, FileSearchOutlined } from '@ant-design/icons'
import { useWorkspaceItems, useDeleteWorkspaceItem } from '../../hooks/useWorkspaces'
import ArtifactList from './ArtifactList'
import ArtifactViewer from './ArtifactViewer'
import type { WorkspaceItemData } from '../../api/workspaces'

const { Title, Text } = Typography

export default function WorkspacePage() {
  const { workspace_id } = useParams<{ workspace_id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, refetch } = useWorkspaceItems(workspace_id || null)
  const deleteMutation = useDeleteWorkspaceItem(workspace_id || '')
  const [selectedItem, setSelectedItem] = useState<WorkspaceItemData | null>(null)

  const handleDelete = useCallback(async (itemId: string) => {
    try {
      await deleteMutation.mutateAsync(itemId)
      message.success('已删除')
      if (selectedItem?.id === itemId) {
        setSelectedItem(null)
      }
    } catch {
      message.error('删除失败')
    }
  }, [deleteMutation, selectedItem])

  const handleView = useCallback((item: WorkspaceItemData) => {
    setSelectedItem(item)
  }, [])

  const handleClose = useCallback(() => {
    setSelectedItem(null)
  }, [])

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  }

  const items = data?.items || []
  const ownerCounts: Record<string, number> = {}
  for (const item of items) {
    ownerCounts[item.owner] = (ownerCounts[item.owner] || 0) + 1
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>返回</Button>
          <Title level={3} style={{ marginBottom: 0 }}>工作空间</Title>
          <Text code>{workspace_id}</Text>
        </Space>
        <Space>
          <Button icon={<FileSearchOutlined />} onClick={() => navigate(`/artifacts?workspace_id=${workspace_id}`)}>搜索产物</Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="Artifact 数量" value={items.length} prefix={<FileOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="创建者数量" value={Object.keys(ownerCounts).length} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* Content */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={selectedItem ? 14 : 24}>
          <Card title="Artifact 列表" size="small">
            <ArtifactList
              items={items}
              loading={isLoading}
              onView={handleView}
              onDelete={handleDelete}
            />
          </Card>
        </Col>
        {selectedItem && (
          <Col xs={24} lg={10}>
            <ArtifactViewer item={selectedItem} onClose={handleClose} />
          </Col>
        )}
      </Row>
    </div>
  )
}
