import React, { useEffect, useState, useRef } from 'react';
import type { NatsConnection, Msg } from 'nats.ws';
import { v4 as uuidv4 } from 'uuid';
import YAML from 'yaml';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface WorkflowDesignerProps {
  nc: NatsConnection | null;
}

interface DagSpec {
  name: string;
  schedule?: string;
  tasks: any[];
}

const WorkflowDesigner: React.FC<WorkflowDesignerProps> = ({ nc }) => {
  const [yamlText, setYamlText] = useState<string>('');
  const [parsedDag, setParsedDag] = useState<DagSpec | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inbox = useRef<string>('');
  const sub = useRef<any>(null);

  // Initialize reply inbox
  useEffect(() => {
    inbox.current = `designer.inbox.${uuidv4()}`;
    if (nc) {
      sub.current = nc.subscribe(inbox.current);
      (async () => {
        for await (const msg of sub.current) {
          handleOrchestratorResponse(msg);
        }
      })();
    }
    return () => {
      if (sub.current) sub.current.unsubscribe();
    };
  }, [nc]);

  // Parse YAML to DAG spec
  const parseYaml = () => {
    try {
      const doc = YAML.parse(yamlText) as DagSpec;
      if (!doc.name || !Array.isArray(doc.tasks)) {
        throw new Error('Missing required fields: name or tasks');
      }
      setParsedDag(doc);
      setError(null);
    } catch (e: any) {
      setError(e.message);
      setParsedDag(null);
    }
  };

  // Send spec to orchestrator for validation
  const validateDag = () => {
    if (!nc || !parsedDag) return;
    const payload = {
      dag: parsedDag,
      replyTo: inbox.current,
    };
    nc.publish('workflow.designer.validate', new TextEncoder().encode(JSON.stringify(payload)));
  };

  const handleOrchestratorResponse = (msg: Msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.data));
      if (data.valid) {
        alert('DAG validated successfully!');
      } else {
        alert(`Validation errors:\n${data.errors.join('\n')}`);
      }
    } catch {
      alert('Unexpected response from orchestrator.');
    }
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      <h2 className="text-xl font-semibold">Workflow Designer</h2>
      <div className="flex-1 flex flex-col">
        <Textarea
          className="flex-1 font-mono"
          placeholder="Paste or write your DAG YAML here..."
          value={yamlText}
          onChange={(e) => setYamlText(e.currentTarget.value)}
        />
        {error && <p className="text-red-600 mt-2">YAML Error: {error}</p>}
      </div>
      <div className="flex space-x-2">
        <Button onClick={parseYaml} disabled={!yamlText}>
          Parse YAML
        </Button>
        <Button onClick={validateDag} disabled={!parsedDag || !nc}>
          Validate & Save
        </Button>
      </div>
      {parsedDag && (
        <pre className="bg-gray-100 p-2 rounded overflow-auto text-sm">
          {JSON.stringify(parsedDag, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default WorkflowDesigner;
