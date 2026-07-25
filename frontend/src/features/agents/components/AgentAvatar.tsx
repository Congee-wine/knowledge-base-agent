import { useEffect, useState } from 'react'
import { getAgentAvatar } from '../../../api/agents'
import type { ChatAgent } from '../../../types/chat'

type AgentAvatarProps = {
  agent: Pick<ChatAgent, 'avatarKey' | 'id' | 'name'>
  className: string
  imageClassName?: string
}

function fallbackLabel(agent: AgentAvatarProps['agent']) {
  return agent.name.slice(0, 1).toUpperCase()
}

export function AgentAvatar({ agent, className, imageClassName }: AgentAvatarProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!agent.avatarKey) {
      setImageUrl(null)
      return
    }

    let active = true
    let objectUrl: string | null = null
    void getAgentAvatar(agent.id)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        if (active) setImageUrl(objectUrl)
        else URL.revokeObjectURL(objectUrl)
      })
      .catch(() => {
        if (active) setImageUrl(null)
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [agent.avatarKey, agent.id])

  return (
    <span className={className}>
      {imageUrl ? <img alt="" className={imageClassName} src={imageUrl} /> : fallbackLabel(agent)}
    </span>
  )
}
