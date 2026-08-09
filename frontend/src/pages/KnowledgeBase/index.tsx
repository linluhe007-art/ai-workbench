import { Card, Typography } from 'antd'
import { DatabaseOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function KnowledgeBase() {
  return (
    <div>
      <Title level={3}>知识库</Title>
      <Card style={{ minHeight: 400 }}>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <DatabaseOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <Paragraph style={{ marginTop: 16, color: '#999' }}>
            知识库管理功能将在 Phase 5 中实现
          </Paragraph>
        </div>
      </Card>
    </div>
  )
}