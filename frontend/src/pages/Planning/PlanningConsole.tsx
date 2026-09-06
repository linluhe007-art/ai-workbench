import { useState } from 'react'
import { Input, Button, Space, Card, Spin, Alert, Typography, Empty } from 'antd'
import { PlayCircleOutlined, ExperimentOutlined } from '@ant-design/icons'
import { usePlanningDebug, usePlanningSessions } from '../../hooks/usePlanning'
import PlanningResult from './PlanningResult'
import PlanningHistory from './PlanningHistory'

const { Title } = Typography
const { TextArea } = Input

export default function PlanningConsole() {
  const [task, setTask] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const debugMutation = usePlanningDebug()
  const { data: historyData, isLoading: historyLoading } = usePlanningSessions()

  const handleRun = () => {
    const trimmed = task.trim()
    if (!trimmed) return
    debugMutation.mutate(trimmed, {
      onSuccess: (session) => {
        setSelectedSessionId(session.session_id)
      },
    })
  }

  const activeSession = selectedSessionId
    ? (historyData?.sessions?.find((s) => s.session_id === selectedSessionId) ?? debugMutation.data)
    : debugMutation.data

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={4}>
        <ExperimentOutlined /> LLM Planner Debug Console
      </Title>

      {/* Input */}
      <Card size="small">
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="输入规划任务..."
            autoSize={{ minRows: 2, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleRun()
              }
            }}
          />
        </Space.Compact>
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={debugMutation.isPending}
            onClick={handleRun}
            disabled={!task.trim()}
          >
            Run Planning
          </Button>
        </div>
      </Card>

      {/* Error */}
      {debugMutation.isError && (
        <Alert
          message="规划失败"
          description={debugMutation.error?.message || '未知错误'}
          type="error"
          showIcon
          closable
        />
      )}

      {/* Result */}
      {debugMutation.isPending && <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />}

      {activeSession && !debugMutation.isPending && (
        <PlanningResult session={activeSession} />
      )}

      {!activeSession && !debugMutation.isPending && !debugMutation.isError && (
        <Empty description="输入任务并点击执行规划查看结果" />
      )}

      {/* History */}
      <PlanningHistory
        sessions={historyData?.sessions || []}
        loading={historyLoading}
        onSelect={(id) => setSelectedSessionId(id)}
      />
    </Space>
  )
}