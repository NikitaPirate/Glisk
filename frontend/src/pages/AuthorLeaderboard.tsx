import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface AuthorLeaderboardEntry {
  author_address: string
  total_tokens: number
}

export default function AuthorLeaderboard() {
  const [authors, setAuthors] = useState<AuthorLeaderboardEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Fetch leaderboard data from API
    fetch('/api/authors/leaderboard')
      .then(res => res.json())
      .then((data: AuthorLeaderboardEntry[]) => {
        setAuthors(data)
        setIsLoading(false)
      })
      .catch(error => {
        console.error('Failed to fetch leaderboard:', error)
        setIsLoading(false)
      })
  }, [])

  // Loading state
  if (isLoading) {
    return <div className="p-8 text-gray-500">Loading...</div>
  }

  // Empty state
  if (authors.length === 0) {
    return <div className="p-8 text-gray-500">No authors yet</div>
  }

  // Leaderboard display
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Top Authors</h1>
      <div className="space-y-2">
        {authors.map((author, index) => (
          <div
            key={author.author_address}
            onClick={() => navigate(`/${author.author_address}`)}
            className="border border-gray-300 rounded p-4 hover:bg-gray-100 cursor-pointer transition-colors"
          >
            <div className="flex justify-between items-center">
              <span className="font-mono text-sm">
                {index + 1}. {author.author_address}
              </span>
              <span className="text-gray-600">
                {author.total_tokens} token{author.total_tokens !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
