import { Card, Tag, Space, Typography, Empty, Statistic, Row, Col } from 'antd'
import { ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons'

const { Text, Title } = Typography

interface CapabilityPanelProps {
  capabilities: string[]
  experience?: {
    task_count: number
    success_rate: number
  }
}

const capColors: Record<string, string> = {
  research: 'blue',
  analysis: 'green',
  writing: 'purple',
  mock: 'default',
  test: 'orange',
  search: 'cyan',
  image: 'magenta',
  seo: 'gold',
}

export default function CapabilityPanel({ capabilities, experience }: CapabilityPanelProps) {
  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          <span>能力面板</span>
        </Space>
      }
      size="small"
    >
      {capabilities.length === 0 ? (
        <Empty description="暂无能力标签" />
      ) : (
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>能力标签</Text>
          <Space size={[8, 8]} wrap>
            {capabilities.map((cap) => (
              <Tag key={cap} color={capColors[cap] || 'default'} style={{ fontSize: 13, padding: '2px 10px' }}>
                {cap}
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {experience && (
        <Row gutter={[16, 8]} style={{ marginTop: 16 }}>
          <Col span={12}>
            <Statistic title="执行次数" value={experience.task_count} prefix={<CheckCircleOutlined />} />
          </Col>
          <Col span={12}>
            <Statistic
              title="成功率"
              value={(experience.success_rate * 100).toFixed(0)}
              suffix="%"
              valueStyle={experience.success_rate >= 0.8 ? { color: '#3f8600' } : undefined}
            />
          </Col>
        </Row>
      )}
    </Card>
  )
}