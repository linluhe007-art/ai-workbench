import { Card, Typography } from 'antd'
import { MessageOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function ChatPage() {
  return (
    <div>
      <Title level={3}>AI 对话</Title>
      <Card style={{ minHeight: 400 }}>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <MessageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <Paragraph style={{ marginTop: 16, color: '#999' }}>
            AI 对话功能将在 Phase 3 (Agent Gateway) 中实现
          </Paragraph>
        </div>
      </Card>
    </div>
  )
}