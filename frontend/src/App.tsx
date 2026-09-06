import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ChatPage from './pages/Chat'
import TaskCenter from './pages/TaskCenter'
import ContentReview from './pages/ContentReview'
import KnowledgeBase from './pages/KnowledgeBase'
import LoginPage from './pages/Login'
import TaskDetail from './pages/TaskDetail/TaskDetail'
import WorkspacePage from './pages/Workspace/Workspace'
import AgentDetail from './pages/AgentDetail/AgentDetail'
import AgentManagement from './pages/AgentManagement/AgentManagement'
import AgentTeam from './pages/AgentTeam'
import PlanningConsole from './pages/Planning/PlanningConsole'
import ArtifactsPage from './pages/Artifacts/Artifacts'
import MetricsDashboard from './pages/Metrics/MetricsDashboard'
import ExperienceExplorer from './pages/Experience/ExperienceExplorer'
import DeveloperConsole from './pages/Developer/DeveloperConsole'
import DeploymentStatus from './pages/Deployment/DeploymentStatus'
import AutomationCenter from './pages/AutomationCenter'
import PersonalDashboard from './pages/PersonalDashboard'
import ImprovementPage from './pages/Improvement'
import ModelSettingsPage from './pages/ModelSettings'
import PersonalOSDashboard from './pages/PersonalOS'
import AIDebugCenter from './pages/AIDebug'
import CommandCenter from './pages/Command/CommandCenter'
import MemoryExplorer from './pages/Memory/MemoryExplorer'
import AuditExplorer from './pages/Audit/AuditExplorer'
import UserManagement from './pages/Auth/UserManagement'
import ResearchConsole from './pages/Research/ResearchConsole'
import SystemStatus from './pages/System/SystemStatus'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="dashboard/personal" element={<PersonalDashboard />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="tasks" element={<TaskCenter />} />
        <Route path="tasks/:task_id" element={<TaskDetail />} />
        <Route path="agents/:agent_id" element={<AgentDetail />} />
        <Route path="agents/manage" element={<AgentManagement />} />
        <Route path="agents/team" element={<AgentTeam />} />
        <Route path="workspaces/:workspace_id" element={<WorkspacePage />} />
        <Route path="artifacts" element={<ArtifactsPage />} />
        <Route path="metrics" element={<MetricsDashboard />} />
        <Route path="experience" element={<ExperienceExplorer />} />
        <Route path="developers" element={<DeveloperConsole />} />
        <Route path="deployment" element={<DeploymentStatus />} />
        <Route path="command" element={<CommandCenter />} />
        <Route path="memory" element={<MemoryExplorer />} />
        <Route path="audit" element={<AuditExplorer />} />
        <Route path="auth" element={<UserManagement />} />
        <Route path="content" element={<ContentReview />} />
        <Route path="knowledge" element={<KnowledgeBase />} />
        <Route path="planning" element={<PlanningConsole />} />
        <Route path="automation" element={<AutomationCenter />} />
        <Route path="improvement" element={<ImprovementPage />} />
        <Route path="models" element={<ModelSettingsPage />} />
        <Route path="os" element={<PersonalOSDashboard />} />
        <Route path="research" element={<ResearchConsole />} />
        <Route path="ai-debug" element={<AIDebugCenter />} />
        <Route path="system" element={<SystemStatus />} />
      </Route>
    </Routes>
  )
}

export default App
