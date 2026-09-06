import React from "react"
import { Card, Table, Tag, Typography, Spin, Alert, Row, Col, Statistic } from "antd"
import { CheckCircleOutlined, ClusterOutlined, CrownOutlined } from "@ant-design/icons"
import { useCluster } from "../../hooks/useDeployment"

const { Title } = Typography

const DeploymentStatus: React.FC = () => {
  const { data, isLoading, error } = useCluster()

  if (isLoading) return <div style={{ padding: 48, textAlign: "center" }}><Spin size="large" /></div>
  if (error) return <Alert type="error" message="加载集群数据失败" description={String(error)} />

  const cols = [
    { title: "实例", dataIndex: "instance_id", key: "id" },
    { title: "角色", dataIndex: "role", key: "role", render: (r: string) => r === "leader" ? <Tag color="gold" icon={<CrownOutlined />}>主节点</Tag> : <Tag>工作节点</Tag> },
    { title: "状态", dataIndex: "status", key: "status", render: (s: string) => <Tag color="green" icon={<CheckCircleOutlined />}>{s}</Tag> },
    { title: "启动时间", dataIndex: "started_at", key: "started", render: (t: string) => t ? new Date(t).toLocaleString() : "-" },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}><ClusterOutlined /> Deployment Status</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="实例数" value={data?.total ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="主节点" value={data?.leader || "N/A"} /></Card></Col>
        <Col span={6}><Card><Statistic title="持久化" value={data?.health?.persistence ?? "unknown"} /></Card></Col>
        <Col span={6}><Card><Statistic title="Redis" value={data?.health?.redis ?? "unknown"} /></Card></Col>
      </Row>

      <Card title="集群实例">
        <Table dataSource={data?.instances || []} columns={cols} rowKey="instance_id" pagination={false} size="middle" />
      </Card>
    </div>
  )
}

export default DeploymentStatus