# Granite-Copilot-for-Workflow  
*A self-correcting, multi-agent automation framework powered by IBM Granite models*

---

## 1. What it is  
**Granite-Copilot-for-Workflow (GCW)** turns IBM’s open, enterprise-grade **Granite** foundation models into a “copilot” that *plans → executes → verifies → corrects* every step of a business or DevOps workflow.  
Granite supplies the natural-language reasoning; a mesh of containerised agents (build, test, security, compliance, doc-gen …) supply deterministic checks; the orchestrator keeps looping until everything is green or a human signs off. The result is hands-free pipelines with auditable AI guard-rails. Granite models are available open-source on GitHub and watsonx.ai under Apache-2.0 licences  ([IBM Granite - GitHub](https://github.com/ibm-granite), [Foundation Models - IBM watsonx.ai](https://www.ibm.com/products/watsonx-ai/foundation-models)).

---

## 2. Top-level Features  
| Capability | How GCW does it |
|------------|-----------------|
| **Plain-English Workflow Design** | Granite LLM (8 B/20 B *-Instruct* or local 3 B) turns “Ship v2.3 and publish docs” into a DAG of tasks with parameters. |
| **Execution–Verify–Correct Loop** | Each task result is routed to verification agents (tests, OPA, SCA, etc.). Failures trigger auto-fix agents or human escalation. |
| **Pluggable Agents** | Drop in new docker images that expose a simple NATS RPC schema. |
| **Traceability & Audit** | Every LLM thought, rule, and test result is stored in Neo4j for provenance. |
| **Hybrid Deployment** | One-liner **docker-compose up** for laptops; Helm charts for k8s. |
| **Extensible UI** | React/TypeScript frontend with chat, workflow designer and log viewer. |

---

## 3. Example Use-flow  

> **User:** *“Create a nightly workflow that builds `main`, runs unit + security tests, generates release notes from merged PRs, and deploys to staging only if all checks pass.”*

1. **Planner Agent** (Granite call) → Task-DAG YAML.  
2. **Orchestrator** schedules *Build*, *Unit Test*, *SCA Scan* in parallel.  
3. **Verification Agents** report success for build/tests, but SCA finds a CVE.  
4. **Auto-Fix Agent** asks Granite to propose a safe version bump → updates `package.json`.  
5. Loop runs again → all green → **Deploy Agent** pushes to staging.  
6. **Doc-Gen Agent** uses Granite-Code to draft release notes → **Style Linter** validates.  
7. Orchestrator marks run complete and posts an audit link in Slack with rule traces.

---

## 4. Repository Layout  

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

---

## 5. Setup & Quick-start  

```bash
# 1. Clone and configure
git clone https://github.com/ruslanmv/granite-copilot-workflow.git
cd granite-copilot-workflow
cp .env.template .env             # add WATSONX_APIKEY etc.

# 2. Launch demo topology
docker compose build
docker compose up -d

# 3. Open the UI
open http://localhost:3000

# 4. Chat example
> “Generate a workflow to build, test, scan, and deploy my Python app.”
```

*In VS Code?* – install the **“GCW-CLI”** extension and run `GCW: New Workflow` to chat-design a pipeline inside your repo.  

---

## 6. Core Configuration  

```yaml
# orchestrator/config.yaml
llm:
  provider: watsonx          # or 'local'
  model_id: ibm/granite-13b-instruct-v2
  timeout_secs: 60

bus:
  nats_url: nats://nats:4222

verify_timeouts:
  build:     600
  test:      300
  security:  400
  compliance:300
  doc:       120
  autofix:   180

graph:
  neo4j_uri: bolt://neo4j:7687
  user: neo4j
  password: neo4j

```

Agents auto-discover tasks by subscribing to subjects like `task.build.*` or `verify.security.*`.

---

## 7. Developing New Agents  

1. **Create a container** exposing `/app/agent.py` with a class that implements  
   ```python
   async def handle(self, task_msg): ...
   ```  
2. **Add mapping** in `config.yaml` → `agents:` section.  
3. **Publish** Docker image and add to `docker-compose.override.yml`.  
4. **Declare verify rules** (if needed) in `opa/policies/` – the orchestrator pushes artefacts to OPA automatically.

---

## 8. Verification Toolkit Out-of-the-box  

| Check | Tool |
|-------|------|
| Unit & integration tests | PyTest / JUnit |
| Security dependencies | Snyk CLI or Trivy |
| Static analysis | Ruff / ESLint |
| IaC policy | Open Policy Agent |
| Doc style & term ontology | Vale + company-term OWL |
| Governance | SPDX SBOM diff |

---

## 9. How to Extend Workflows  

* **Add human approvals:** Set `requires_approval: true` in DAG YAML to pause and ping Slack (Observer Agent).  
* **Conditionals & loops:** Use Jinja-style expressions in YAML; Planner Agent expands them.  
* **Multi-repo orchestration:** Each build agent instance isolates a repo; Orchestrator aggregates results before continuing.  

---

## 10. CI for GCW itself  

* `pre-commit` with Ruff, Black, and Reuse-lint.  
* GitHub Actions matrix tests for Python 3.10-3.12.  
* Cypress tests for the React frontend.  
* Nightly e2e run on `examples/nightly_build.yaml`.

---

## 11. Roadmap  

| Quarter | Milestone |
|---------|-----------|
| Q2-2025 | SaaS demo on IBM Cloud · GPT-RAG chat history search |
| Q3-2025 | Multi-tenant auth, RBAC · Plugin marketplace |
| Q4-2025 | Agent auto-scaling on K8s HPA · Time-series-driven execution optimisation |
| 2026    | No-code canvas designer powered by Granite multimodal models  ([IBM Expands Granite Model Family with New Multi-Modal and ...](https://newsroom.ibm.com/2025-02-26-ibm-expands-granite-model-family-with-new-multi-modal-and-reasoning-ai-built-for-the-enterprise)) |

---

## 12. Contributing  

PRs welcome! Start with `docs/extending.md`, sign the CLA, follow commit style `feat(scope): msg`. We run DCO checks.

---

## 13. License  

Apache 2.0 (same as Granite models)  ([Foundation Models - IBM watsonx.ai](https://www.ibm.com/products/watsonx-ai/foundation-models))

---

### Recap  

*GCW* gives you a **chat-based autopilot** that converts business intent into safe, documented, self-healing automation. Clone, set your Granite credentials, spin up Docker, and start shipping workflows that verify themselves before you hit *prod*. Happy automating! 🚀