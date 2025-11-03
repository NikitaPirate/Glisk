import { CreatorMintPageClient } from './ClientPage'

export default async function CreatorMintPage({
  params,
}: {
  params: Promise<{ creatorAddress: string }>
}) {
  const { creatorAddress } = await params
  return <CreatorMintPageClient creatorAddress={creatorAddress} />
}
