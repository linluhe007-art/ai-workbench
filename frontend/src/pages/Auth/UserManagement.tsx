import { useState } from 'react'
import {
  Tabs,
  Table,
  Tag,
  Typography,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Alert,
  Spin,
  Empty,
  Popconfirm,
  message,
} from 'antd'
import {
  UserOutlined,
  TeamOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  useUsers,
  useCreateUser,
  useDeleteUser,
  useRoles,
  useCreateRole,
  useDeleteRole,
  useAllPermissions,
} from '../../hooks/useAuth'
import type { UserRecord, RoleRecord } from '../../api/auth'

const { Title, Text } = Typography

export default function UserManagement() {
  const [activeTab, setActiveTab] = useState('users')
  const [userModalOpen, setUserModalOpen] = useState(false)
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [userForm] = Form.useForm()
  const [roleForm] = Form.useForm()

  const { data: usersData, isLoading: usersLoading, isError: usersError, refetch: refetchUsers } = useUsers()
  const { data: rolesData, isLoading: rolesLoading, isError: rolesError, refetch: refetchRoles } = useRoles()
  const { data: permissionsData } = useAllPermissions()

  const createUserMutation = useCreateUser()
  const deleteUserMutation = useDeleteUser()
  const createRoleMutation = useCreateRole()
  const deleteRoleMutation = useDeleteRole()

  // User table columns
  const userColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) => (
        <Space size={4} wrap>
          {roles.map((r: string) => (
            <Tag key={r} color="blue">{r.replace('role-', '')}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (ts: string) => new Date(ts).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserRecord) => (
        <Popconfirm
          title="确定删除该用户？"
          onConfirm={() => {
            deleteUserMutation.mutate(record.id, {
              onSuccess: () => message.success('用户已删除'),
              onError: (e) => message.error(`Failed: ${e}`),
            })
          }}
        >
          <Button size="small" danger loading={deleteUserMutation.isPending}>
            Delete
          </Button>
        </Popconfirm>
      ),
    },
  ]

  // Role table columns
  const roleColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '权限',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (perms: string[]) => (
        <Space size={4} wrap>
          {perms.map((p: string) => <Tag key={p}>{p}</Tag>)}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: RoleRecord) => (
        <Popconfirm
          title="确定删除该角色？"
          onConfirm={() => {
            deleteRoleMutation.mutate(record.id, {
              onSuccess: () => message.success('角色已删除'),
              onError: (e) => message.error(`Failed: ${e}`),
            })
          }}
        >
          <Button size="small" danger loading={deleteRoleMutation.isPending}>
            Delete
          </Button>
        </Popconfirm>
      ),
    },
  ]

  const handleCreateUser = async () => {
    try {
      const values = await userForm.validateFields()
      createUserMutation.mutate(values, {
        onSuccess: () => {
          message.success('用户创建成功')
          setUserModalOpen(false)
          userForm.resetFields()
        },
        onError: (e) => message.error(`Failed: ${e}`),
      })
    } catch {
      // validation failed
    }
  }

  const handleCreateRole = async () => {
    try {
      const values = await roleForm.validateFields()
      createRoleMutation.mutate(values, {
        onSuccess: () => {
          message.success('角色创建成功')
          setRoleModalOpen(false)
          roleForm.resetFields()
        },
        onError: (e) => message.error(`Failed: ${e}`),
      })
    } catch {
      // validation failed
    }
  }

  const permissionOptions = permissionsData?.permissions.map((p) => ({
    value: p.key,
    label: `${p.key} (${p.name})`,
  })) || []

  return (
    <div>
      <Title level={4}><TeamOutlined /> User & Role Management</Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'users',
          label: <span><UserOutlined /> Users</span>,
          children: (
            <div>
              <Space style={{ marginBottom: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setUserModalOpen(true)}>
                  Create User
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => refetchUsers()}>刷新</Button>
              </Space>

              {usersError && <Alert type="error" message="加载用户失败" showIcon style={{ marginBottom: 16 }} />}
              {usersLoading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
              {!usersLoading && !usersError && usersData && usersData.users.length === 0 && (
                <Empty description="未找到用户" />
              )}
              {!usersLoading && !usersError && usersData && usersData.users.length > 0 && (
                <Table columns={userColumns} dataSource={usersData.users} rowKey="id" size="small" />
              )}

              <Modal
                title="创建用户"
                open={userModalOpen}
                onOk={handleCreateUser}
                onCancel={() => { setUserModalOpen(false); userForm.resetFields() }}
                confirmLoading={createUserMutation.isPending}
              >
                <Form form={userForm} layout="vertical">
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="roles" label="角色">
                    <Select mode="tags" placeholder="例如：role-viewer" />
                  </Form.Item>
                </Form>
              </Modal>
            </div>
          ),
        },
        {
          key: 'roles',
          label: <span><TeamOutlined /> Roles</span>,
          children: (
            <div>
              <Space style={{ marginBottom: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setRoleModalOpen(true)}>
                  Create Role
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => refetchRoles()}>刷新</Button>
              </Space>

              {rolesError && <Alert type="error" message="加载角色失败" showIcon style={{ marginBottom: 16 }} />}
              {rolesLoading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
              {!rolesLoading && !rolesError && rolesData && rolesData.roles.length === 0 && (
                <Empty description="未找到角色" />
              )}
              {!rolesLoading && !rolesError && rolesData && rolesData.roles.length > 0 && (
                <Table columns={roleColumns} dataSource={rolesData.roles} rowKey="id" size="small" />
              )}

              <Modal
                title="创建角色"
                open={roleModalOpen}
                onOk={handleCreateRole}
                onCancel={() => { setRoleModalOpen(false); roleForm.resetFields() }}
                confirmLoading={createRoleMutation.isPending}
              >
                <Form form={roleForm} layout="vertical">
                  <Form.Item name="name" label="角色名称" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="description" label="描述" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="permissions" label="权限">
                    <Select mode="multiple" placeholder="选择权限" options={permissionOptions} />
                  </Form.Item>
                </Form>
              </Modal>
            </div>
          ),
        },
      ]} />
    </div>
  )
}