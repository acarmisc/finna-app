import React from 'react'

interface SkeletonBlockProps {
  width?: string | number
  height?: string | number
  className?: string
  style?: React.CSSProperties
}

export function SkeletonBlock({ width = '100%', height = 14, className, style }: SkeletonBlockProps) {
  return (
    <div
      className={`skel${className ? ` ${className}` : ''}`}
      style={{ width, height, ...style }}
    />
  )
}

export default SkeletonBlock