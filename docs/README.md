# Usage Guide – Granite Copilot for Workflow
Everything you need to **run, extend, and benefit from GCW** in one place.

---

## 1 . Who should use GCW?
| Use-case | Why GCW helps |
|----------|---------------|
| **DevOps & Platform** engineers drowning in brittle CI/CD YAML | GCW converts plain-English release instructions into a *self-verifying* DAG, auto-fixes failures, and ships artefacts only after every rule passes. |
| **Security / Compliance** teams with “gating” spreadsheets | Turn OPA/ODM rules into on-path agents; GCW bumps PRs that violate policy *before* they merge. |
| **Docs & Release** managers chasing change-logs | LLM-powered *DocAgent* writes release notes from merged PRs and pushes to Confluence after successful builds. |
| **LoB teams building prototypes** that need guard-rails | Start locally with Docker Compose; swap Granite for small local LLM if no cloud. |

You **should not** use GCW as a generic chat bot or data-science notebook; it is opinionated toward **workflow orchestration with safety loops**.

---

## 2 . Prerequisites
* Docker 20.10+ and Docker Compose v2  
* Git (for cloning build sources)  
* IBM watsonx.ai credentials **or** local Granite GGUF file  
* (Optional) Slack webhook for notifications  
* Ports **4222**, **7474**, **7687**, **8080**, **8181**, **3000** free on your host  

---

## 3 . First-run (Laptop)
```bash
# Clone
git clone https://github.com/ruslanmv/granite-copilot-workflow.git
cd granite-copilot-workflow

# Configure
cp .env.template .env        # add WATSONX_APIKEY, etc.

# Build & lift entire stack
docker compose build
docker compose up -d

# UI
open http://localhost:3000         # Chat / Designer / Logs
```
The first start downloads ≈1 GB of images (NATS, Neo4j, OPA, agents, frontend).

---

## 4 . Daily Workflow

### 4.1 Describe a pipeline in Chat
```
> “Every night at 02:00 build main, run unit + snyk, generate release notes and deploy to staging.”
```
* **PlannerAgent** → YAML DAG  
* You approve / tweak in the Designer tab  
* Orchestrator schedules next run via cron in Neo4j

### 4.2 Trigger ad-hoc run
```bash
curl -X POST http://localhost:8080/api/workflows/<wfId>/runs \
     -H "Content-Type: application/json" \
     -d '{"overrides":{"build_args":{"DEBUG":1}}}'
```

### 4.3 Watch & debug
* Real-time logs stream in **LogsViewer** (Web UI)  
* Failing tasks appear red; click to view agent output  
* **AutoFixAgent** patches simple issues (vuln bump, lint fix) and re-queues task  

---

## 5 . Kubernetes Deployment (optional)

```bash
kubectl apply -f kubernetes/nats-neo4j-opa.yaml
kubectl apply -f kubernetes/orchestrator-deployment.yaml
kubectl apply -f kubernetes/agents-statefulset.yaml
```
*Expose Orchestrator via an Ingress with TLS in production.*

---

## 6 . Extending

| Want to… | Do this |
|----------|---------|
| **Add an agent** | `agents/my_agent/{agent.py,Dockerfile,requirements.txt}`, set `subject:` and build image; list in `orchestrator/config.yaml → agents`. |
| **Enforce a new rule** | Add `.rego` under `policies/compliance/`, the ComplianceAgent bundles automatically. |
| **Swap LLM** | Set `llm.provider: local` and `model_id: ./models/granite-3b.gguf` in config, mount model into *doc_agent* / *auto_fix_agent*. |
| **Integrate Jira** | Create `jira_agent`, subscribe to `task.jira.create.request`, and emit `.response`. |

---

## 7 . Advantages at a glance
* **Self-Correcting** – Execution → Verification → Correction loop prevents “green-but-broken” pipelines.  
* **Declarative Safety** – OPA + ODM rules live next to code; audits show *why* a decision passed.  
* **Observable** – Neo4j graph = provenance; Prom / OTEL exported by ObserverAgent.  
* **LLM-agnostic** – Swap Granite cloud → local with one config change.  
* **Zero-lock-in** – Plain Docker, Apache-2.0 license, no proprietary SaaS endpoints.

---

## 8 . FAQ
**Q:** *Does GCW replace my existing GitHub Actions?*  
**A:** No. GCW can *orchestrate* Actions via an agent, or run standalone. Use whichever executor suits your org.

**Q:** *Can I disable AutoFix?*  
**A:** Yes—remove `auto_fix_agent` from `config.yaml` or use `verify_timeouts.autofix: 0`.

**Q:** *How big is Granite 13 B?*  
**A:** ~23 GB in fp16; use the 3 B (~6 GB) model locally if resources are tight.

---

## 9 . Need help?
* **Docs:** see [`docs/architecture.md`](architecture.md), [`docs/api_reference.md`](api_reference.md), [`docs/extending.md`](extending.md),[`docs/example.md`](example.md). 
   
* **Issues / PRs:** open on the GitHub repo.  
* **Community:** #granite-copilot on IBM-slack / Discord.
