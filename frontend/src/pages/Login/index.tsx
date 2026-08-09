import { Card, Typography } from 'antd'
import { LockOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function LoginPage() {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: '#f0f2f5',
    }}>
      <Card style={{ width: 400, textAlign: 'center' }}>
        <LockOutlined style={{ fontSize: 48, color: '#1677ff', marginBottom: 16 }} />
        <Title level={3}>AI Content Workbench</Title>
        <Paragraph type="secondary">
          登录功能将在 Phase 2 (用户系统) 中实现
        </Paragraph>
      </Card>
    </div>
  )
}