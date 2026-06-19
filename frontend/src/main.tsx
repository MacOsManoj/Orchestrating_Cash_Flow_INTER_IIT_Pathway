import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AssetProvider } from './context/AssetContext';
import 'flexlayout-react/style/dark.css';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AssetProvider>
        <App />
      </AssetProvider>
    </BrowserRouter>
  </React.StrictMode>
);
