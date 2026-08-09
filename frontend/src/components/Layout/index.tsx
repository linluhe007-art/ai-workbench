import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme, Avatar, Space, Typography } from 'antd'
import {
  DashboardOutlined,
  MessageOutlined,
  ProjectOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  RobotOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout
const { Title } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/chat', icon: <MessageOutlined />, label: 'AI 对话' },
  { key: '/tasks', icon: <ProjectOutlined />, label: '任务中心' },
  { key: '/content', icon: <FileTextOutlined />, label: '内容审核' },
  { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={220}
      >
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Space>
            <RobotOutlined style={{ fontSize: 24, color: '#1677ff' }} />
            {!collapsed && (
              <Title level={4} style={{ color: '#fff', margin: 0 }}>
                AI Workbench
              </Title>
            )}
          </Space>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Space>
            <Avatar icon={<RobotOutlined />} />
            <span>Admin</span>
          </Space>
        </Header>
        <Content style={{
          margin: '24px',
          padding: '24px',
          background: colorBgContainer,
          borderRadius: borderRadiusLG,
          minHeight: 280,
          overflow: 'auto',
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}