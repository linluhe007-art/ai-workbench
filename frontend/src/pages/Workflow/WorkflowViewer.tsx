import { useCallback, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Node, type Edge } from 'reactflow'
import 'reactflow/dist/style.css'
import { Card, Col, Empty, Row, Space, Tag, Typography } from 'antd'
import { BranchesOutlined } from '@ant-design/icons'
import type { WorkflowData, WorkflowStep } from '../../api/workflows'
import StepNode from './StepNode'
import StepDetailPanel from './StepDetailPanel'

const { Text } = Typography

interface WorkflowViewerProps {
  workflow: WorkflowData | undefined
  loading?: boolean
}

const statusColors: Record<string, string> = {
  pending: '#d9d9d9',
  running: '#1677ff',
  success: '#52c41a',
  failed: '#ff4d4f',
  skipped: '#bfbfbf',
}

// Custom node component
function CustomNode({ data }: { data: { step: WorkflowStep } }) {
  return <StepNode data={data.step} />
}

const nodeTypes = { stepNode: CustomNode }

export default function WorkflowViewer({ workflow, loading }: WorkflowViewerProps) {
  const [selectedStep, setSelectedStep] = useState<WorkflowStep | null>(null)

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const step = node.data?.step as WorkflowStep
    if (step) setSelectedStep(step)
  }, [])

  const handleClose = useCallback(() => setSelectedStep(null), [])

  // Build React Flow nodes and edges from workflow data
  const { nodes, edges } = useMemo(() => {
    if (!workflow?.steps) return { nodes: [], edges: [] }

    const steps = workflow.steps
    const stepMap = new Map(steps.map((s) => [s.id, s]))

    // Compute levels for layout (topological)
    const levels = computeLevels(steps)

    // Build nodes with positions
    const flowNodes: Node[] = []
    const xGap = 220
    const yGap = 100

    for (const [level, stepIds] of levels.entries()) {
      for (const [idx, stepId] of stepIds.entries()) {
        const step = stepMap.get(stepId)!
        flowNodes.push({
          id: step.id,
          type: 'stepNode',
          position: { x: level * xGap, y: idx * yGap },
          data: { step },
        })
      }
    }

    // Build edges from dependencies
    const flowEdges: Edge[] = []
    for (const step of steps) {
      for (const depId of step.depends_on) {
        if (stepMap.has(depId)) {
          flowEdges.push({
            id: `${depId}-${step.id}`,
            source: depId,
            target: step.id,
            animated: step.status === 'running',
            style: { stroke: statusColors[step.status] || '#d9d9d9', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: statusColors[step.status] || '#d9d9d9' },
          })
        }
      }
    }

    return { nodes: flowNodes, edges: flowEdges }
  }, [workflow])

  if (!workflow || workflow.steps.length === 0) {
    return <Empty description="暂无 Workflow 数据" />
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={selectedStep ? 16 : 24}>
        <Card
          title={
            <Space>
              <BranchesOutlined />
              <span>Workflow 任务图</span>
              <Tag>{workflow.total_steps} 步骤</Tag>
            </Space>
          }
          size="small"
          bodyStyle={{ padding: 0, height: 400 }}
          loading={loading}
        >
          <div style={{ width: '100%', height: 400 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
        </Card>
      </Col>
      {selectedStep && (
        <Col xs={24} lg={8}>
          <StepDetailPanel step={selectedStep} onClose={handleClose} />
        </Col>
      )}
    </Row>
  )
}

// ── Helpers ──────────────────────────────────────────────────

function computeLevels(steps: WorkflowStep[]): Map<number, string[]> {
  const stepMap = new Map(steps.map((s) => [s.id, s]))
  const levels = new Map<number, string[]>()
  const assigned = new Map<string, number>()

  function getLevel(stepId: string): number {
    if (assigned.has(stepId)) return assigned.get(stepId)!
    const step = stepMap.get(stepId)
    if (!step || step.depends_on.length === 0) {
      assigned.set(stepId, 0)
      return 0
    }
    const maxDep = Math.max(...step.depends_on.map((d) => getLevel(d)))
    const level = maxDep + 1
    assigned.set(stepId, level)
    return level
  }

  for (const step of steps) {
    const level = getLevel(step.id)
    if (!levels.has(level)) levels.set(level, [])
    levels.get(level)!.push(step.id)
  }

  return levels
}