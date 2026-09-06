import { Card, Typography, Empty } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography

interface WriterPreviewProps {
  content: string
}

function renderMarkdownLines(content: string) {
  if (!content) return null
  const lines = content.split('\n')
  return lines.map((line, i) => {
    if (line.startsWith('# ')) {
      return <Title key={i} level={2}>{line.replace('# ', '')}</Title>
    }
    if (line.startsWith('## ')) {
      return <Title key={i} level={3} style={{ marginTop: 20 }}>{line.replace('## ', '')}</Title>
    }
    if (line.startsWith('### ')) {
      return <Title key={i} level={4}>{line.replace('### ', '')}</Title>
    }
    if (line.startsWith('- ')) {
      return <Paragraph key={i} style={{ paddingLeft: 16, marginBottom: 4 }}>• {line.replace('- ', '')}</Paragraph>
    }
    if (line.match(/^\d+\./)) {
      return <Paragraph key={i} style={{ paddingLeft: 16, marginBottom: 4 }}>{line}</Paragraph>
    }
    if (line.startsWith('---')) {
      return <div key={i} style={{ borderTop: '1px solid #e8e8e8', margin: '16px 0' }} />
    }
    if (line.startsWith('*') && line.endsWith('*')) {
      return <Paragraph key={i} type="secondary">{line.replace(/\*/g, '')}</Paragraph>
    }
    if (line.trim() === '') {
      return <div key={i} style={{ height: 8 }} />
    }
    return <Paragraph key={i} style={{ marginBottom: 8 }}>{line}</Paragraph>
  })
}

export default function WriterPreview({ content }: WriterPreviewProps) {
  if (!content) {
    return <Empty description="尚未生成内容" />
  }

  return (
    <Card
      size="small"
      title={<span><FileTextOutlined /> Preview</span>}
      style={{ background: '#fafafa' }}
    >
      <div style={{ maxHeight: 600, overflow: 'auto', padding: 16 }}>
        {renderMarkdownLines(content)}
      </div>
    </Card>
  )
}

