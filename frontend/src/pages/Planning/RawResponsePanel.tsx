import { Card, Collapse, Typography, Tag } from 'antd'
import { CodeOutlined } from '@ant-design/icons'

const { Text } = Typography

interface RawResponsePanelProps {
  rawResponse: string | null
}

export default function RawResponsePanel({ rawResponse }: RawResponsePanelProps) {
  if (!rawResponse) return null

  return (
    <Card title="LLM 原始响应" size="small" extra={<CodeOutlined />}>
      <Collapse
        size="small"
        items={[{
          key: 'raw',
          label: <span>查看原始响应 <Tag>{rawResponse.length} chars</Tag></span>,
          children: (
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12, background: '#fafafa', padding: 12, borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
              {rawResponse}
            </pre>
          ),
        }]}
      />
    </Card>
  )
}