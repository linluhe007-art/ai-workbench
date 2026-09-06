import { Card, Steps, Tag, Typography, Empty, Spin, Button, Space, Descriptions } from 'antd'
import { BulbOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useTaskTrace } from '../../hooks/useAIDebug'
import type { DecisionTrace } from '../../api/aiDebug'

const { Title, Text } = Typography

const traceStepLabels: Record<string, { title: string; icon: string; color: string }> = {
  command_analysis: { title: '指令分析', icon: '⌨️', color: 'blue' },
  plan_generation: { title: '规划生成', icon: '📋', color: 'purple' },
  memory_retrieval: { title: '记忆检索', icon: '🧠', color: 'green' },
  agent_selection: { title: 'Agent 选择', icon: '🤖', color: 'orange' },
  workflow_selection: { title: 'Workflow 选择', icon: '🔀', color: 'cyan' },
  tool_selection: { title: '工具选择', icon: '🔧', color: 'magenta' },
  final_result: { title: '最终结果', icon: '✅', color: 'red' },
}

const statusFromConfidence = (c: number) => (c >= 0.8 ? 'finish' : c >= 0.5 ? 'process' : 'wait')

interface Props {
  taskId: string | null
}

export default function ExecutionTracePanel({ taskId }: Props) {
  const { data, isLoading, isError, refetch } = useTaskTrace(taskId)

  if (!taskId) {
    return <Empty description="未提供任务 ID" />
  }

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="正在加载执行轨迹..." /></div>
  }

  if (isError || !data) {
    return (
      <Card>
        <Empty description="加载执行轨迹失败">
          <Button onClick={() => refetch()}>重试</Button>
        </Empty>
      </Card>
    )
  }

  const traces: DecisionTrace[] = data.traces || []

  if (traces.length === 0) {
    return (
      <Card>
        <Empty description="该任务暂无执行轨迹">
          <Text type="secondary">当 AI 在任务执行期间做出决策时，会记录执行轨迹。</Text>
        </Empty>
      </Card>
    )
  }

  // Sort traces by creation time for the chain
  const sorted = [...traces].sort((a, b) => a.created_at.localeCompare(b.created_at))

  return (
    <div>
      {/* AI Explain header */}
      <Card size="small" style={{ marginBottom: 16, background: '#f6ffed' }}>
        <Space>
          <BulbOutlined style={{ color: '#52c41a', fontSize: 18 }} />
          <div>
            <Text strong>AI 决策链</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              Complete trace of AI reasoning from command analysis to final result
            </Text>
          </div>
        </Space>
      </Card>

      {/* Decision chain steps */}
      <Card title={<Space><ThunderboltOutlined /> Execution Trace</Space>} size="small">
        <Steps
          direction="vertical"
          size="small"
          current={sorted.length}
          items={sorted.map((trace) => {
            const label = traceStepLabels[trace.trace_type] || { title: trace.trace_type, icon: '📌', color: 'default' }
            return {
              title: (
                <Space>
                  <span>{label.icon}</span>
                  <Text strong>{label.title}</Text>
                  <Tag color={label.color}>{trace.component || 'unknown'}</Tag>
                  <Tag>{`${(trace.confidence * 100).toFixed(0)}%`}</Tag>
                </Space>
              ),
              description: (
                <Card size="small" style={{ background: '#fafafa' }}>
                  <Descriptions size="small" column={1}>
                    {trace.reason && (
                      <Descriptions.Item label="原因">
                        <Text>{trace.reason}</Text>
                      </Descriptions.Item>
                    )}
                    {trace.decision && Object.keys(trace.decision).length > 0 && (
                      <Descriptions.Item label="决策">
                        <Text code style={{ fontSize: 11 }}>{JSON.stringify(trace.decision)}</Text>
                      </Descriptions.Item>
                    )}
                    {trace.input_data && Object.keys(trace.input_data).length > 0 && (
                      <Descriptions.Item label="输入">
                        <Text code style={{ fontSize: 11 }}>{JSON.stringify(trace.input_data)}</Text>
                      </Descriptions.Item>
                    )}
                    {trace.metadata && Object.keys(trace.metadata).length > 0 && (
                      <Descriptions.Item label="元数据">
                        <Text code style={{ fontSize: 11 }}>{JSON.stringify(trace.metadata)}</Text>
                      </Descriptions.Item>
                    )}
                    <Descriptions.Item label="时间">
                      <Text type="secondary" style={{ fontSize: 11 }}>{trace.created_at}</Text>
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              ),
              status: statusFromConfidence(trace.confidence),
            }
          })}
        />
      </Card>
    </div>
  )
}
