import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { CreatorMintPage } from './pages/CreatorMintPage'
import { ProfilePage } from './pages/ProfilePage'
import AuthorLeaderboard from './pages/AuthorLeaderboard'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
          <Route path="/" element={<AuthorLeaderboard />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/:creatorAddress" element={<CreatorMintPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
