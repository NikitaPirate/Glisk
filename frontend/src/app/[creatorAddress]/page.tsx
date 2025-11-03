import { CreatorMintPageClient } from './ClientPage'

// Force dynamic rendering to avoid build-time env variable requirements
export const dynamic = 'force-dynamic'

export default async function CreatorMintPage({
  params,
}: {
  params: Promise<{ creatorAddress: string }>
}) {
  const { creatorAddress } = await params
  return <CreatorMintPageClient creatorAddress={creatorAddress} />
}
