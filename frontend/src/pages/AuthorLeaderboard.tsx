import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Identity, Avatar, Name, Badge, Address } from '@coinbase/onchainkit/identity'
import { Card } from '@/components/ui/card'

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
    return (
      <div className="container mx-auto px-12 py-20 max-w-4xl">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    )
  }

  // Empty state
  if (authors.length === 0) {
    return (
      <div className="container mx-auto px-12 py-20 max-w-4xl">
        <p className="text-sm text-muted-foreground">No authors yet</p>
      </div>
    )
  }

  // Leaderboard display
  return (
    <div className="container mx-auto px-12 py-20 max-w-4xl">
      <Card className="px-8">
        <div className="space-y-6">
          {authors.map((author, index) => (
            <div
              key={author.author_address}
              onClick={() => navigate(`/${author.author_address}`)}
              className="p-6 bg-accent shadow-interactive hover-lift cursor-pointer transition-all"
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground font-semibold min-w-[2rem]">
                    {index + 1}.
                  </span>
                  <Identity address={author.author_address as `0x${string}`}>
                    <Avatar />
                    <Name>
                      <Badge />
                    </Name>
                    <Address />
                  </Identity>
                </div>
                <span className="text-muted-foreground">
                  {author.total_tokens} token{author.total_tokens !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
