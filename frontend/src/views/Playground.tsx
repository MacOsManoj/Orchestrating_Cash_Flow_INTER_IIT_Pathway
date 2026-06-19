import React from 'react';
import { PlaygroundProvider, usePlayground } from '../context/PlaygroundContext';
import { PlaygroundEmpty } from './PlaygroundEmpty';
import { PlaygroundActive } from './PlaygroundActive';

const PlaygroundContent: React.FC = () => {
  const { currentVersion } = usePlayground();

  // Show empty state if no version selected
  if (!currentVersion) {
    return <PlaygroundEmpty />;
  }

  // Show active playground with canvas
  return <PlaygroundActive />;
};

export function Playground() {
  return (
    <PlaygroundProvider>
      <PlaygroundContent />
    </PlaygroundProvider>
  );
}