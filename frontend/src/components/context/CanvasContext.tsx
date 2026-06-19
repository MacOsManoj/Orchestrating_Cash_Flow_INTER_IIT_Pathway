import React, { createContext, useContext, useState, type ReactNode } from 'react';
import type { ComponentConfig } from '../types/CanvasSchema';

interface CanvasContextType {
  components: ComponentConfig[];
  setComponents: (components: ComponentConfig[]) => void;
}

const CanvasContext = createContext<CanvasContextType | undefined>(undefined);

export const useCanvas = () => {
  const context = useContext(CanvasContext);
  if (!context) {
    throw new Error('useCanvas must be used within CanvasProvider');
  }
  return context;
};

interface CanvasProviderProps {
  children: ReactNode;
}

export const CanvasProvider: React.FC<CanvasProviderProps> = ({ children }) => {
  const [components, setComponents] = useState<ComponentConfig[]>([]);
  
  return (
    <CanvasContext.Provider value={{ components, setComponents }}>
      {children}
    </CanvasContext.Provider>
  );
};
