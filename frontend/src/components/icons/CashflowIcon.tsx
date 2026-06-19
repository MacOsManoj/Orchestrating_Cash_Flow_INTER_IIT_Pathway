interface IconProps {
  className?: string;
  size?: number;
}

export const CashflowIcon = ({ className, size = 24 }: IconProps) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 50 50" 
      fill="currentColor" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path d="M10.4167 35.4167V20.8334H14.5834V35.4167H10.4167ZM22.9167 35.4167V20.8334H27.0834V35.4167H22.9167ZM4.16675 43.75V39.5834H45.8334V43.75H4.16675ZM35.4167 35.4167V20.8334H39.5834V35.4167H35.4167ZM4.16675 16.6667V12.5L25.0001 2.08337L45.8334 12.5V16.6667H4.16675ZM13.4376 12.5H36.5626L25.0001 6.77087L13.4376 12.5Z" fill="currentColor"/>
    </svg>
  );
};
