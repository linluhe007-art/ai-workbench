import { Card, Typography } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function ContentReview() {
  return (
    <div>
      <Title level={3}>内容审核</Title>
      <Card style={{ minHeight: 400 }}>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <FileTextOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <Paragraph style={{ marginTop: 16, color: '#999' }}>
            内容审核功能将在 Phase 5 (Content Pipeline) 中实现
          </Paragraph>
        </div>
      </Card>
    </div>
  )
}