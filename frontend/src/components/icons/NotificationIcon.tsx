interface IconProps {
  className?: string;
  size?: number;
}

export const NotificationIcon = ({ className, size = 24 }: IconProps) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 44 44" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M22 38C24.2091 38 26 36.2091 26 34H18C18 36.2091 19.7909 38 22 38Z" fill="currentColor"/>
      <path d="M36 28V18C36 11.372 31.098 5.86 25 4.54V2C25 0.895431 24.1046 0 23 0H21C19.8954 0 19 0.895431 19 2V4.54C12.902 5.86 8 11.372 8 18V28L4 32V34H40V32L36 28Z" fill="currentColor"/>
    </svg>
  );
};
