##  Repository Layout  

```
granite-copilot-workflow/
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.yml
├── .env.template
├── orchestrator/
│   ├── main.py
│   ├── config.yaml
│   ├── config.py 
│   ├── bus.py
│   ├── llm_client.py
│   └── graph_tracer.py
├── agents/
│   ├── planner_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── build_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── test_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── security_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── compliance_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── doc_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── auto_fix_agent/
│   │   ├── agent.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── observer_agent/
│       ├── agent.py
│       ├── requirements.txt
│       └── Dockerfile
├── frontend/
│   ├── package.json
│   ├── tsconfig.json               
│   ├── vite.config.ts              
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── ChatWindow.tsx
│           ├── WorkflowDesigner.tsx
│           └── LogsViewer.tsx
├── examples/
│   ├── nightly_build.yaml
│   └── quickstart.sh
├── docs/
│   ├── architecture.md
│   ├── extending.md
│   └── api_reference.md
├── kubernetes/
│   ├── orchestrator-deployment.yaml
│   ├── agents-statefulset.yaml
│   └── nats-neo4j-opa.yaml
└── policies/                       
    └── compliance/                 
        └── policy.rego            

```
