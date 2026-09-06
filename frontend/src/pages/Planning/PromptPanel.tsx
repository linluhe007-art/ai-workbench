import { Card, Collapse, Typography } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'

const { Paragraph } = Typography

interface PromptPanelProps {
  prompt: string | null
}

export default function PromptPanel({ prompt }: PromptPanelProps) {
  if (!prompt) return null

  return (
    <Card title="提示词" size="small" extra={<FileTextOutlined />}>
      <Collapse
        size="small"
        items={[{
          key: 'prompt',
          label: '查看完整 提示词',
          children: (
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 12, background: '#fafafa', padding: 12, borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
              {prompt}
            </pre>
          ),
        }]}
        defaultActiveKey={['prompt']}
      />
    </Card>
  )
}
