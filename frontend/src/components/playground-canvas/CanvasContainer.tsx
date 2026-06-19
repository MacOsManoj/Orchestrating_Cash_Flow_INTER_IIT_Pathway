import React from 'react';
import { useCanvas } from '../context/CanvasContext';
import { ComponentMap } from '../playground-components';

export const CanvasContainer: React.FC = () => {
  const { components } = useCanvas();
  
  if (components.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[400px] border-2 border-dashed border-gray-300 rounded-lg bg-'#0C1E1E'">
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
          </svg>
          <p className="text-gray-500 text-lg font-medium">No components loaded</p>
          <p className="text-gray-400 text-sm mt-2">Select a version from the left panel to begin</p>
        </div>
      </div>
    );
  }
  
  return (
    <div
      className="grid grid-cols-1  gap-6 p-4 rounded-lg"
      style={{ backgroundColor: '#0B141A' }}
    >
      {components.map((config) => {
        const Component = ComponentMap[config.type];
        if (!Component) {
          return (
            <div key={config.id} className="bg-red-50 border border-red-300 rounded-lg p-4">
              <p className="text-red-600 font-semibold">⚠️ Component Not Found</p>
              <p className="text-red-500 text-sm mt-1">"{config.type}" is not registered in ComponentMap</p>
            </div>
          );
        }
        return <Component key={config.id} {...config.data} />;
      })}
    </div>
  );
};
