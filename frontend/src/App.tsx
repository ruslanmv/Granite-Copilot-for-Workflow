import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from 'react-query';
import { connect } from 'nats.ws';
import ChatWindow from './components/ChatWindow';
import WorkflowDesigner from './components/WorkflowDesigner';
import LogsViewer from './components/LogsViewer';
import './index.css';

const queryClient = new QueryClient();

const App: React.FC = () => {
  // UI tab state
  const [activeTab, setActiveTab] = useState<'chat' | 'designer' | 'logs'>('chat');
  // NATS connection
  const [nc, setNc] = useState<any>(null);

  useEffect(() => {
    // Connect to NATS server on mount
    (async () => {
      try {
        const nc = await connect({ servers: import.meta.env.VITE_NATS_URL });
        setNc(nc);
      } catch (err) {
        console.error('Failed to connect to NATS:', err);
      }
    })();
    // Cleanup on unmount
    return () => {
      if (nc) nc.close();
    };
  }, []);

  const renderTab = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatWindow nc={nc} />;
      case 'designer':
        return <WorkflowDesigner nc={nc} />;
      case 'logs':
        return <LogsViewer />;
      default:
        return null;
    }
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <header className="bg-white shadow flex items-center px-6 h-16">
          <h1 className="text-2xl font-semibold text-gray-800">Granite Copilot for Workflow</h1>
          <nav className="ml-auto space-x-4">
            <button
              className={`px-4 py-2 rounded ${
                activeTab === 'chat' ? 'bg-blue-600 text-white' : 'text-blue-600 hover:bg-blue-100'
              }`}
              onClick={() => setActiveTab('chat')}
            >
              Chat
            </button>
            <button
              className={`px-4 py-2 rounded ${
                activeTab === 'designer' ? 'bg-blue-600 text-white' : 'text-blue-600 hover:bg-blue-100'
              }`}
              onClick={() => setActiveTab('designer')}
            >
              Designer
            </button>
            <button
              className={`px-4 py-2 rounded ${
                activeTab === 'logs' ? 'bg-blue-600 text-white' : 'text-blue-600 hover:bg-blue-100'
              }`}
              onClick={() => setActiveTab('logs')}
            >
              Logs
            </button>
          </nav>
        </header>
        <main className="flex-1 overflow-auto p-6">{renderTab()}</main>
      </div>
    </QueryClientProvider>
  );
};

// Mount to #root
const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<App />);
}

export default App;
