import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ChatPage from './pages/Chat'
import TaskCenter from './pages/TaskCenter'
import ContentReview from './pages/ContentReview'
import KnowledgeBase from './pages/KnowledgeBase'
import LoginPage from './pages/Login'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="tasks" element={<TaskCenter />} />
        <Route path="content" element={<ContentReview />} />
        <Route path="knowledge" element={<KnowledgeBase />} />
      </Route>
    </Routes>
  )
}

export default App