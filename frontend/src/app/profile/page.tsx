import { Suspense } from 'react'
import { ProfilePageClient } from './ClientPage'

// Force dynamic rendering to avoid build-time env variable requirements
export const dynamic = 'force-dynamic'

export default function ProfilePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ProfilePageClient />
    </Suspense>
  )
}
