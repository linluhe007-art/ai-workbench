import { Card, Col, Row, Statistic, Typography } from 'antd'
import {
  FileTextOutlined,
  ProjectOutlined,
  MessageOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'

const { Title, Paragraph } = Typography

export default function Dashboard() {
  return (
    <div>
      <Title level={3}>工作台</Title>
      <Paragraph type="secondary">
        AI 内容运营工作台 — Phase 1 基础环境已就绪
      </Paragraph>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日任务"
              value={0}
              prefix={<ProjectOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="内容数量"
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="对话次数"
              value={0}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已发布"
              value={0}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>快速开始</Title>
        <Paragraph>
          当前为 Phase 1 基础环境。后续将逐步接入 AI Agent、任务编排、内容生产等功能。
        </Paragraph>
      </Card>
    </div>
  )
}