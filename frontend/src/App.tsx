import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Header } from './components/Header'
import { CreatorMintPage } from './pages/CreatorMintPage'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <Routes>
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
