import { useQuery } from '@tanstack/react-query'

export function useEthPrice() {
  return useQuery({
    queryKey: ['eth-price'],
    queryFn: async () => {
      const response = await fetch('https://api.coinbase.com/v2/exchange-rates?currency=ETH')
      if (!response.ok) {
        throw new Error('Failed to fetch ETH price')
      }
      const data = await response.json()
      return parseFloat(data.data.rates.USD)
    },
    staleTime: 60000, // 60 seconds
    refetchInterval: 60000, // Auto-refresh every minute
    retry: 2,
  })
}
