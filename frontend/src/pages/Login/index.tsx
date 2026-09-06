import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Typography, Form, Input, Button, message, Select, Space } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { login } from '../../api/auth'
import { useQueryClient } from '@tanstack/react-query'

const { Title, Paragraph } = Typography

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const handleLogin = async (values: { username: string; password: string; tenant_id?: string }) => {
    setLoading(true)
    try {
      await login({
        username: values.username,
        password: values.password,
        tenant_id: values.tenant_id || '',
      })
      message.success('登录成功')
      qc.invalidateQueries({ queryKey: ['auth-context'] })
      navigate('/dashboard')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '登录失败'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: '#f0f2f5',
    }}>
      <Card style={{ width: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <LockOutlined style={{ fontSize: 48, color: '#1677ff', marginBottom: 16 }} />
          <Title level={3} style={{ margin: 0 }}>AI 工作台</Title>
          <Paragraph type="secondary">登录你的账户</Paragraph>
        </div>

        <Form
          onFinish={handleLogin}
          initialValues={{ username: 'admin', tenant_id: '' }}
          layout="vertical"
          size="large"
        >
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>

          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" autoComplete="current-password" />
          </Form.Item>

          <Form.Item name="tenant_id">
            <Select placeholder="租户（可选）" allowClear>
              <Select.Option value="">默认租户</Select.Option>
              <Select.Option value="tenant-default">默认租户</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Sign In
            </Button>
          </Form.Item>
        </Form>

        <Paragraph type="secondary" style={{ textAlign: 'center', fontSize: 12 }}>
          Default: admin / admin
        </Paragraph>
      </Card>
    </div>
  )
}