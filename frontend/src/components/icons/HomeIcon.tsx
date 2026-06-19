interface IconProps {
  className?: string;
  size?: number;
}

export const HomeIcon = ({ className, size = 24 }: IconProps) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 52 52" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M8 21L26 4L44 21V44C44 45.0609 43.5786 46.0783 42.8284 46.8284C42.0783 47.5786 41.0609 48 40 48H12C10.9391 48 9.92172 47.5786 9.17157 46.8284C8.42143 46.0783 8 45.0609 8 44V21Z" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M20 48V28H32V48" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
};
