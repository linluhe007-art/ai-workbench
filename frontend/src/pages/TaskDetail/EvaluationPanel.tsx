import { Card, Progress, Tag, Typography, Descriptions, Empty, Space } from 'antd'
import { ThunderboltOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'

const { Text, Title } = Typography

interface EvaluationPanelProps {
  score?: number
  quality?: string
  issues?: string[]
}

const scoreColor = (score: number) => {
  if (score >= 8) return '#52c41a'
  if (score >= 6) return '#faad14'
  return '#ff4d4f'
}

const qualityTag = (quality: string) => {
  switch (quality) {
    case 'excellent': return <Tag color="success" icon={<CheckCircleOutlined />}>优秀</Tag>
    case 'good': return <Tag color="processing">良好</Tag>
    case 'fair': return <Tag color="warning" icon={<WarningOutlined />}>一般</Tag>
    case 'poor': return <Tag color="error">较差</Tag>
    default: return <Tag>{quality}</Tag>
  }
}

export default function EvaluationPanel({ score, quality, issues }: EvaluationPanelProps) {
  if (score === undefined) {
    return <Empty description="暂无评估数据" />
  }

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          <span>质量评估</span>
        </Space>
      }
      size="small"
    >
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <Progress
          type="dashboard"
          percent={Math.round(score * 10)}
          format={() => (
            <div>
              <Title level={3} style={{ margin: 0, color: scoreColor(score) }}>
                {score.toFixed(1)}
              </Title>
              <Text type="secondary">/10</Text>
            </div>
          )}
          strokeColor={scoreColor(score)}
          size={120}
        />
      </div>

      {quality && (
        <div style={{ textAlign: 'center', marginBottom: 12 }}>
          {qualityTag(quality)}
        </div>
      )}

      {issues && issues.length > 0 && (
        <div>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>问题列表：</Text>
          {issues.map((issue, i) => (
            <Tag key={i} color="warning" style={{ marginBottom: 4 }}>
              {issue}
            </Tag>
          ))}
        </div>
      )}
    </Card>
  )
}