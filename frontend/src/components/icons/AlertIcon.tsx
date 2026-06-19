interface IconProps {
  className?: string;
  size?: number;
}

export const AlertIcon = ({ className, size = 24 }: IconProps) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 45 45" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M22.5 4.5L40.5 36H4.5L22.5 4.5Z" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M22.5 16.5V24" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="22.5" cy="30" r="1.5" fill="currentColor"/>
    </svg>
  );
};
