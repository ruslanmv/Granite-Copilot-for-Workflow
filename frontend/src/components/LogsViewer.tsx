import React, { useEffect, useState, useRef } from 'react';
import type { NatsConnection, Msg } from 'nats.ws';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  message: string;
}

interface LogsViewerProps {
  nc: NatsConnection | null;
}

const LogsViewer: React.FC<LogsViewerProps> = ({ nc }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<string>('INFO');
  const sub = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Subscribe to log stream on mount
  useEffect(() => {
    if (!nc) return;
    sub.current = nc.subscribe('workflow.logs.stream');
    (async () => {
      for await (const msg of sub.current) {
        handleLogMessage(msg);
      }
    })();
    return () => {
      if (sub.current) sub.current.unsubscribe();
    };
  }, [nc]);

  const handleLogMessage = (msg: Msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.data));
      const entry: LogEntry = {
        id: data.id,
        timestamp: data.timestamp,
        level: data.level,
        message: data.message,
      };
      setLogs((prev) => [...prev, entry].slice(-200)); // keep last 200 entries
      // auto-scroll
      containerRef.current?.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    } catch (err) {
      console.error('Invalid log message', err);
    }
  };

  const filteredLogs = logs.filter((entry) => {
    if (filter === 'ALL') return true;
    return entry.level === filter;
  });

  return (
    <div className="flex flex-col h-full p-4">
      <div className="flex items-center mb-2 space-x-2">
        <label htmlFor="levelFilter" className="font-medium">
          Level:
        </label>
        <select
          id="levelFilter"
          className="border rounded px-2 py-1"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="ALL">ALL</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARN">WARN</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto bg-gray-50 border rounded p-2 font-mono text-sm"
      >
        {filteredLogs.map((entry) => (
          <div
            key={entry.id}
            className={`mb-1 ${
              entry.level === 'ERROR'
                ? 'text-red-600'
                : entry.level === 'WARN'
                ? 'text-yellow-700'
                : entry.level === 'DEBUG'
                ? 'text-gray-600'
                : 'text-gray-800'
            }`}
          >
            <span className="font-semibold">[{entry.timestamp}]</span>{' '}
            <span className="font-medium">[{entry.level}]</span>{' '}
            <span>{entry.message}</span>
          </div>
        ))}
        {filteredLogs.length === 0 && (
          <div className="text-gray-500 italic">No logs to display.</div>
        )}
      </div>
    </div>
  );
};

export default LogsViewer;
