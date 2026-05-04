// Delegator to unified Badge component
import { Badge } from './badge'

interface SeverityBadgeProps {
  severity: string
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return <Badge variant="severity" value={severity} className={className} />
}

export default SeverityBadge