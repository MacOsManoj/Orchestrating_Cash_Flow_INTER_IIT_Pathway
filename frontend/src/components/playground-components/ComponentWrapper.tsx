import React from 'react'

interface ComponentWrapperProps {
  children: React.ReactNode
  className?: string
}

export const ComponentWrapper: React.FC<ComponentWrapperProps> = ({
  children,
  className = ''
}) => {
  return (
    <div className={`
      w-full h-full
      bg-[#0f1419] 
      border border-gray-800 
      rounded-lg 
      p-2 sm:p-2.5 md:p-3
      overflow-auto
      flex flex-col
      ${className}
    `}>
      {children}
    </div>
  )
}