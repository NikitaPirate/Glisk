import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Header } from './components/Header'
import { CreatorMintPage } from './pages/CreatorMintPage'
import { CreatorDashboard } from './pages/CreatorDashboard'
import { ProfileSettings } from './pages/ProfileSettings'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/creator-dashboard" element={<CreatorDashboard />} />
          <Route path="/profile-settings" element={<ProfileSettings />} />
          <Route path="/:creatorAddress" element={<CreatorMintPage />} />
          <Route
            path="/"
            element={<Navigate to="/0x0000000000000000000000000000000000000000" replace />}
          />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
