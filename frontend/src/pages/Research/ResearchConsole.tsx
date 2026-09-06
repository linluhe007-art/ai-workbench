import { useState } from 'react'
import { Card, Input, Select, Button, Typography, Space, Spin, Tag, message } from 'antd'
import { SearchOutlined, ExperimentOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons'
import { startResearch } from '../../api/research'
import WriterPreview from './WriterPreview'
import SourceList from './SourceList'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const OUTPUT_TYPES = [
  { value: 'report', label: '研究报告' },
  { value: 'article', label: '文章' },
  { value: 'analysis', label: '分析' },
]

export default function ResearchConsole() {
  const [query, setQuery] = useState('')
  const [outputType, setOutputType] = useState('report')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [sources, setSources] = useState<any[]>([])
  const [taskId, setTaskId] = useState('')
  const [error, setError] = useState('')

  const handleResearch = async () => {
    if (!query.trim()) {
      message.warning('请输入研究主题')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    setSources([])

    try {
      const res = await startResearch({ query: query.trim(), output_type: outputType, max_sources: 10 })
      setTaskId(res.task_id)
      message.success(`研究完成！共找到 ${res.source_count} 个来源`)

      // Fetch sources
      const sourcesRes = await fetch(`/api/v1/research/${res.task_id}/sources`).then(r => r.json())
      setSources(sourcesRes.sources || [])

      // Fetch result
      const resultRes = await fetch(`/api/v1/research/${res.task_id}/result`).then(r => r.json())
      setResult(resultRes.artifact || resultRes)
    } catch (err: any) {
      setError(err.message || '研究失败')
      message.error('研究失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={3}>
        <ExperimentOutlined /> 智能研究
      </Title>
      <Paragraph type="secondary">
        输入主题，让 AI 搜索、分析并为你生成结构化报告。
      </Paragraph>

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>研究主题</Text>
            <TextArea
              placeholder='例如：“分析 2026 年 AI Agent 市场趋势”'
              value={query}
              onChange={e => setQuery(e.target.value)}
              rows={3}
              style={{ marginTop: 8 }}
            />
          </div>
          <div>
            <Text strong>输出格式</Text>
            <Select
              value={outputType}
              onChange={setOutputType}
              options={OUTPUT_TYPES}
              style={{ width: 200, marginLeft: 16 }}
            />
          </div>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleResearch}
            loading={loading}
            size="large"
          >
            开始研究
          </Button>
        </Space>
      </Card>

      {loading && (
        <Card>
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <Paragraph style={{ marginTop: 16 }}>
              <Tag color="processing">正在搜索网页...</Tag>
              <Tag color="processing">正在提取信息...</Tag>
              <Tag color="processing">正在生成报告...</Tag>
            </Paragraph>
          </div>
        </Card>
      )}

      {error && (
        <Card>
          <Text type="danger">{error}</Text>
        </Card>
      )}

      {result && (
        <>
          <Card
            title={<Space><FileTextOutlined />研究结果</Space>}
            style={{ marginBottom: 24 }}
            extra={<Tag color="green">已完成</Tag>}
          >
            <WriterPreview content={result.content || ''} />
          </Card>

          {sources.length > 0 && (
            <Card
              title={<Space><LinkOutlined />来源（{sources.length}）</Space>}
              style={{ marginBottom: 24 }}
            >
              <SourceList sources={sources} />
            </Card>
          )}
        </>
      )}
    </div>
  )
}
