import { useQuery } from '@tanstack/react-query'
import { getAgents } from '../../../api/agents'
import { agentKeys } from '../agentKeys'

export function useAgents() {
  return useQuery({ queryKey: agentKeys.all, queryFn: getAgents })
}
