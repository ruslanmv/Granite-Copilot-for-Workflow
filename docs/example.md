# Granite-Copilot-for-Workflow — Hands-On Examples  
*A step-by-step tour from `docker compose up` to self-healing pipelines.*

---

## 0 · Prerequisites

| Tool                              | Version | Notes                                                         |
|-----------------------------------|---------|---------------------------------------------------------------|
| Docker / Docker Compose           | 20.10+  | Compose V2 syntax (`docker compose …`).                       |
| Git                                | 2.30+  | To clone the repo.                                            |
| IBM Cloud / watsonx.ai API key **or** local Granite model | — | Copy creds into `.env`.                                       |
| (Optional) Node 18+ / Python 3.11+ | —       | For extending agents or the frontend.                         |

---

## 1 · Clone & Launch

```bash
git clone https://github.com/ruslanmv/granite-copilot-workflow.git
cd granite-copilot-workflow

# copy secrets template ➜ edit WATSONX_APIKEY, etc.
cp .env.template .env

docker compose build     # first run: ~1 GB images
docker compose up -d
```

Open **<http://localhost:3000>** when the containers are healthy.  
You’ll see:

* **Chat** — natural-language prompts.  
* **Workflow Designer** — YAML / drag-and-drop DAG editor.  
* **Logs Viewer** — live task output and Neo4j provenance links.

---

## 2 · Example #1 — Nightly Build ➡ Security Scan ➡ Staging Deploy

### 2.1 Describe the Goal (Chat)

```
“Every night at 02:00 UTC build the main branch of repo acme-api,
run unit tests, dependency scan, generate release notes,
and deploy to the staging namespace only if everything passes.”
```

### 2.2 What Happens

1. **PlannerAgent** (Granite 13 B) converts the sentence to a DAG.  
2. **Orchestrator** writes a `Run` node in Neo4j and schedules tasks via NATS.  
3. **Build / Test / Security** agents run in parallel.  
4. If all pass ➜ **DeployAgent** performs `helm upgrade`.  
5. **DocAgent** drafts release notes and publishes to Confluence.  
6. **ObserverAgent** pushes a Slack summary with the Neo4j run-URL.

### 2.3 Generated DAG (auto-saved in Neo4j + MinIO)

```yaml
name: nightly-acme-api
schedule: "0 2 * * *"        # cron UTC
tasks:
  - id: checkout
    type: git-clone
    repo: git@github.com:acme/api.git
    branch: main

  - id: build
    type: docker-build
    context: ./api
    image: registry.acme.local/api:${{ run.id }}

  - id: unit_tests
    type: pytest
    needs: [build]

  - id: dep_scan
    type: snyk
    target: registry.acme.local/api:${{ run.id }}
    needs: [build]

  - id: deploy_staging
    type: helm-upgrade
    chart: ./chart
    namespace: staging
    image_tag: ${{ run.id }}
    needs: [unit_tests, dep_scan]

  - id: release_notes
    type: llm-doc
    template: docs/templates/relnotes.md.j2
    data_source: github-prs
    needs: [deploy_staging]
```

*(You can tweak YAML in the Designer before saving.)*

---

## 3 · Example #2 — One-Line Ad-hoc Workflow via CLI

```bash
gcw run \
  --name "one-off-load-test" \
  --task git-clone,repo=https://github.com/acme/api.git,branch=feat/opt \
  --task docker-build,context=./api \
  --task k6-load,url=https://staging.api.acme.local,hatch_rate=50
```

The CLI converts each `--task` into DAG nodes, streams logs, and writes provenance.

---

## 4 · Example #3 — Failure → Auto-Fix Loop

1. `dep_scan` flags **CVE-2025-12345** in `express 4.17.1`.  
2. **AutoFixAgent** prompts Granite:  
   > “Upgrade express to the nearest secure minor version preserving semver.”  
3. Granite suggests `4.18.5`, patches `package.json`.  
4. Orchestrator re-queues *build → tests → dep_scan*.  
5. If still vulnerable, AutoFix escalates on Slack:

   > *express 4.18.5 still vulnerable. Manual decision required.*  
   > `gcw logs run/abc123`  

---

## 5 · Inspecting Provenance

Neo4j Browser (http://localhost:7474):

```cypher
MATCH (r:Run {id:"abc123"})--(n) RETURN r,n
```

This shows `Run → Task → Agent` relations for audits.

---

## 6 · Adding Your Own Agent (2 min demo)

```bash
cd agents
copilot new my_static_analysis_agent    # scaffolds files
```

*`agent.py` skeleton*

```python
class MyStaticAnalysisAgent(BaseAgent):
    subject = "verify.static.mytool"

    async def handle(self, task):
        repo = task["workspace"]
        result = subprocess.run(["mytool", repo], capture_output=True)
        ok = result.returncode == 0
        return {"status": "pass" if ok else "fail",
                "log": result.stdout.decode()}
```

```bash
docker build -t gcw/mytool-agent .
docker compose up -d mytool-agent
```

Update DAG:

```yaml
- id: my_static_analysis
  type: verify.static.mytool
  needs: [build]
```

---

## 7 · Clean-up

```bash
docker compose down -v   # stop & remove volumes
rm -rf neo4j-data/*      # wipe provenance (optional)
```

---

## 8 · Troubleshooting

| Symptom                | Fix |
|------------------------|-----|
| **LLM timeout**        | Increase `llm.timeout_secs` in `orchestrator/config.yaml`, or switch to a smaller model. |
| **Circular dependencies** | `gcw dag lint nightly_build.yaml` |
| **Agent can’t reach NATS** | Verify `NATS_URL` in agent env, check Docker network. |

---

## 9 · Next Steps

* **Bring your own Granite model:** drop a GGUF into `models/` and set `llm.provider: local`.  
* **Integrate Jira:** add a `jira_agent`, subscribe to `task.jira.create.request`.  
* **Scale:** apply manifests in `kubernetes/` on your cluster.  
* **Contribute:** see [`docs/extending.md`](../docs/extending.md).

```