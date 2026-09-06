import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme, Avatar, Space, Typography } from 'antd'
import {
  DashboardOutlined,
  BugOutlined,
  WindowsOutlined,
  ApiOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  MessageOutlined,
  ProjectOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  RobotOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  AuditOutlined,
  SafetyOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  BulbOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout
const { Title } = Typography

const menuItems = [
  { key: '/os', icon: <WindowsOutlined />, label: 'AI 工作台' },
  { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/command', icon: <ThunderboltOutlined />, label: '智能指令' },
  { key: '/memory', icon: <BulbOutlined />, label: '长期记忆' },
  { key: '/chat', icon: <MessageOutlined />, label: 'AI 对话' },
  { key: '/tasks', icon: <ProjectOutlined />, label: '任务中心' },
  { key: '/planning', icon: <ExperimentOutlined />, label: '任务规划' },
  { key: '/artifacts', icon: <FileSearchOutlined />, label: '产物中心' },
  { key: '/metrics', icon: <LineChartOutlined />, label: '系统监控' },
  { key: '/audit', icon: <AuditOutlined />, label: '审计日志' },
  { key: '/auth', icon: <SafetyOutlined />, label: '用户与权限' },
  { key: '/content', icon: <FileTextOutlined />, label: '内容审核' },
  { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
  { key: '/improvement', icon: <TrophyOutlined />, label: '自我优化' },
  { key: '/models', icon: <ApiOutlined />, label: '模型配置' },
  { key: '/research', icon: <ExperimentOutlined />, label: '智能研究' },
  { key: '/ai-debug', icon: <BugOutlined />, label: 'AI 调试' },
  { key: '/automation', icon: <ClockCircleOutlined />, label: '自动化' },
  { key: '/agents/manage', icon: <RobotOutlined />, label: 'Agent 管理' },
  { key: '/agents/team', icon: <RobotOutlined />, label: 'Agent 团队' },
  { key: '/system', icon: <DatabaseOutlined />, label: '系统状态' },
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
                AI 工作台
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
            <span>管理员</span>
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

