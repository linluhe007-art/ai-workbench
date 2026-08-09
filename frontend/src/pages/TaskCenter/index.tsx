import { Card, Typography } from 'antd'
import { ProjectOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function TaskCenter() {
  return (
    <div>
      <Title level={3}>任务中心</Title>
      <Card style={{ minHeight: 400 }}>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <ProjectOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <Paragraph style={{ marginTop: 16, color: '#999' }}>
            任务编排功能将在 Phase 4 (Orchestrator) 中实现
          </Paragraph>
        </div>
      </Card>
    </div>
  )
}