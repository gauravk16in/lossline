import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
import { ClerkProvider } from '@clerk/react';

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined;
if (!publishableKey) throw new Error('VITE_CLERK_PUBLISHABLE_KEY is required');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={publishableKey}><App /></ClerkProvider>
  </React.StrictMode>
);
