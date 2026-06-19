import React from 'react';
import { useCanvas } from '../context/CanvasContext';
import {
  canvasSchemaVersionA,
  canvasSchemaVersionB,
  // canvasSchemaVersionC,
  // canvasSchemaVersionD,
  // canvasSchemaVersionE,
} from '../types/CanvasSchema';

export const ChatPanel: React.FC = () => {
  const { setComponents } = useCanvas();

  const versions = [
    {
      name: 'Version 1',
      schema: canvasSchemaVersionA,
      color: 'bg-blue-600 hover:bg-blue-700',
      description: '4 Components: Alerts + Event Timeline + Risk Wheel + Holdings',
    },
    {
      name: 'Version 2',
      schema: canvasSchemaVersionB,
      color: 'bg-green-600 hover:bg-green-700',
      description: '4 Components: News Sentiment + Rates/Yields + AI Insight + FX Correlation',
    },
    // {
    //   name: 'Version 3',
    //   schema: canvasSchemaVersionC,
    //   color: 'bg-purple-600 hover:bg-purple-700',
    //   description: '7 Components: Policy Diff + Sentiment/Vol + Correlations + Heatmap + Movers + Holdings + Attribution',
    // },
    // {
    //   name: 'Version 4',
    //   schema: canvasSchemaVersionD,
    //   color: 'bg-amber-600 hover:bg-amber-700',
    //   description: '7 Components: Risk Sensitivities + Risk Map + Liquidity/Compliance + Credit + ALM',
    // },
    // {
    //   name: 'Version 5',
    //   schema: canvasSchemaVersionE,
    //   color: 'bg-rose-600 hover:bg-rose-700',
    //   description: '9 Components: Cashflows + Liquidity Buffer + Capital Efficiency + Optimization + Stress Tests + Comparisons',
    // },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0C1E1E] p-4 rounded-lg text-white">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Versions</h2>
      </div>

      <div className="space-y-4">
        {versions.map((version) => (
          <button
            key={version.name}
            onClick={() => setComponents(version.schema)}
            className={`w-full ${version.color} text-white px-6 py-4 rounded-lg font-medium transition-all shadow-md hover:shadow-lg text-left`}
          >
            <div className="font-semibold text-lg">{version.name}</div>
            <div className="text-sm text-white/80 mt-1">{version.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
};
