// Delegator to unified Badge component
import { Badge } from './badge'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return <Badge variant="status" value={status} className={className} />
}

export default StatusBadge