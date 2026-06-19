import React from 'react';

interface TabTriggerProps {
  title: string;
  onClick: () => void;
  onClose?: () => void;
}

const TabTrigger: React.FC<TabTriggerProps> = ({ title, onClick, onClose }) => {
  return (
    <button
      className="inline-flex items-center justify-center whitespace-nowrap px-3 h-9 text-sm font-medium group"
      onClick={() => onClick()}
    >
      <span className="truncate">{title}</span>

      {/* Replace nested <button> with span + keyboard support */}
      <span
        role="button"
        tabIndex={0}
        aria-label={`Close ${title}`}
        onClick={(e) => {
          e.stopPropagation();
          onClose?.();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            onClose?.();
          }
        }}
        className="ml-1 transition-all rounded hover:bg-[#008080]/20 p-0.5 opacity-0 group-hover:opacity-100 cursor-pointer"
      >
        <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M6 6 L18 18 M6 18 L18 6"/>
        </svg>
      </span>
    </button>
  );
};

export default TabTrigger;