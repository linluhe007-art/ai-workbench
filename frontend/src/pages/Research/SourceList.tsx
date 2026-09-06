import { List, Tag, Typography, Empty } from 'antd'
import { LinkOutlined, ClockCircleOutlined } from '@ant-design/icons'

const { Text } = Typography

interface SourceItem {
  title: string
  url: string
  snippet?: string
  published?: string
  source?: string
  relevance_score?: number
}

interface SourceListProps {
  sources: SourceItem[]
}

export default function SourceList({ sources }: SourceListProps) {
  if (!sources || sources.length === 0) {
    return <Empty description="未找到来源" />
  }

  return (
    <List
      dataSource={sources}
      renderItem={(item: SourceItem, i: number) => (
        <List.Item key={i}>
          <List.Item.Meta
            title={
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                <LinkOutlined style={{ marginRight: 8 }} />
                {item.title || 'Untitled'}
              </a>
            }
            description={
              <div>
                {item.snippet && <Text type="secondary" style={{ fontSize: 12 }}>{item.snippet}</Text>}
                <div style={{ marginTop: 4 }}>
                  {item.source && <Tag style={{ fontSize: 10 }}>{item.source}</Tag>}
                  {item.published && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {item.published}
                    </Text>
                  )}
                  {item.relevance_score !== undefined && (
                    <Tag color="blue" style={{ fontSize: 10 }}>
                      Score: {(item.relevance_score * 100).toFixed(0)}%
                    </Tag>
                  )}
                </div>
              </div>
            }
          />
        </List.Item>
      )}
    />
  )
}
