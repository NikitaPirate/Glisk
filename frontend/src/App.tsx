import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { sdk } from '@farcaster/miniapp-sdk'
import { Header } from './components/Header'
import { CreatorMintPage } from './pages/CreatorMintPage'
import { ProfilePage } from './pages/ProfilePage'
import AuthorLeaderboard from './pages/AuthorLeaderboard'

function App() {
  // Signal to Base App that the miniapp is ready
  useEffect(() => {
    sdk.actions.ready()
  }, [])

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
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
