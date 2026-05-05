// Delegator to unified Badge component
import { Badge } from './badge'

interface ProviderBadgeProps {
  provider: 'azure' | 'gcp' | 'llm' | 'aws' | string
  size?: 'sm' | 'lg'
  className?: string
}

export function ProviderBadge({ provider, size = 'sm', className }: ProviderBadgeProps) {
  return <Badge variant="provider" value={provider} size={size} className={className} />
}

export default ProviderBadge