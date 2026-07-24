import { useQuery } from '@tanstack/react-query'
import { getAgent } from '../../../api/agents'
import { agentKeys } from '../agentKeys'

export function useAgent(agentId: string | undefined) {
  return useQuery({
    queryKey: agentKeys.detail(agentId ?? ''),
    queryFn: () => getAgent(agentId!),
    enabled: Boolean(agentId),
  })
}
