# Granite-Copilot-for-Workflow – Hands-On Examples  
*A quick tour from “docker compose up” to fully-verified deployments.*

---

## 0 . Prerequisites  

| Tool | Version | Notes |
|------|---------|-------|
| Docker / Docker Compose | 20.10+ | Compose V2 syntax (`docker compose …`). |
| Git | 2.30+ | To clone the repo. |
| IBM Cloud / watsonx.ai API key *or* local Granite model |   | Copy values into `.env`. |
| (Optional) Node 18+ / Python 3.11+ | For agents you may extend. |

---

## 1 . Clone & Launch  

```bash
git clone https://github.com/your-org/granite-copilot-workflow.git
cd granite-copilot-workflow
cp .env.template .env                 # add WATSONX_APIKEY=<…>
docker compose build
docker compose up -d
```

*When all containers are healthy, open <http://localhost:3000>.*  
You should see the **GCW Dashboard** with:

* **Chat panel** – talk to the copilot.  
* **Workflow Designer** – drag-and-drop or paste YAML.  
* **Run Log** – real-time status + Neo4j provenance link.

---

## 2 . Example #1 – Nightly Build → Security Scan → Staging Deploy  

### 2.1 Describe the Goal (Chat)  

> **You:** “Every night at 02:00 UTC build the `main` branch of repo `acme-api`, run unit tests, dependency scan, generate release notes, and deploy to the `staging` namespace only if everything passes.”

### 2.2 What Happens  

1. **Planner Agent** (Granite) turns your sentence into the DAG below.  
2. **Orchestrator** schedules tasks through NATS.  
3. **Build / Test / Security Agents** run in parallel.  
4. **Verification Agents** sign off; if green → `deploy_staging`.  
5. **Doc Agent** pushes release notes to Confluence.  
6. **Observer Agent** sends Slack summary + a Neo4j link.

### 2.3 Generated DAG (auto-saved in Neo4j & S3)  

```yaml
# nightly_build.yaml
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

*(The YAML is produced by the LLM; you can tweak it in the UI before saving.)*

---

## 3 . Example #2 – Instant Ad-hoc Workflow with CLI  

Sometimes chat is overkill. The GCW CLI lets you fire one-liner workflows.

```bash
gcw run \
  --name "one-off-load-test" \
  --task git-clone,repo=https://github.com/acme/api.git,branch=feat/opt \
  --task docker-build,context=./api \
  --task k6-load,url=https://staging.api.acme.local,hatch_rate=50
```

The CLI wraps each `--task` into a DAG node and streams logs until finished.  
Artifacts and traces still land in Neo4j + MinIO.

---

## 4 . Example #3 – Failure & Auto-Fix Loop  

1. **Scenario:** `dep_scan` flags CVE-2025-12345 in `express 4.17.1`.  
2. **Auto-Fix Agent** prompts Granite:

   ```
   "Upgrade express to the nearest secure minor version preserving semver."
   ```

3. Granite suggests **4.18.5** and patches `package.json`.  
4. **Orchestrator** reruns *build → tests → dep_scan.*  
5. If still failing, the agent escalates on Slack with a trace:

   > `express 4.18.5` still vulnerable. Manual decision required.  
   > `gcw logs run/abc123` for details.

---

## 5 . Inspecting Provenance  

*Each run* is a node in Neo4j with relationships:

```
(:Run {id:"abc123"})-[:HAS_TASK]->(:Task {id:"unit_tests"})-[:USED_AGENT]->(:Agent {name:"pytest"})
```

Open **Neo4j Browser** at <http://localhost:7474> and execute:

```cypher
MATCH (r:Run {id:"abc123"})--(n) RETURN r,n
```

You’ll see the graph of tasks, agents, and test verdicts—ideal for audits.

---

## 6 . Adding Your Own Agent (2 mins)  

```bash
cd agents
copilot new my_static_analysis_agent
# scaffold creates Dockerfile + agent.py
```

*agent.py* skeleton:

```python
class MyStaticAnalysisAgent(BaseAgent):
    subject = "verify.static.mytool"

    async def handle(self, task):
        repo = task["workspace"]
        result = subprocess.run(["mytool", repo], capture_output=True)
        status = "pass" if result.returncode == 0 else "fail"
        return {"status": status, "log": result.stdout.decode()}
```

Build & plug in:

```bash
docker build -t gcw/mytool-agent .
docker compose up -d mytool-agent
```

Add to DAG:

```yaml
- id: my_static_analysis
  type: verify.static.mytool
  needs: [build]
```

---

## 7 . Clean-up  

```bash
docker compose down -v    # stop & remove volumes
rm -rf neo4j/data/*       # wipe provenance if you like
```

---

## 8 . Troubleshooting  

| Symptom | Fix |
|---------|-----|
| “LLM timeout” | Increase `llm.timeout` in `orchestrator/config.yaml` or use local Granite 3 B. |
| Circular dependencies | CLI: `gcw dag lint nightly_build.yaml` |
| Agent can’t reach bus | Check `NATS_URL` env & docker network. |

---

## 9 . Next Steps  

* **Bring your own Granite model.** Drop the GGUF into `models/` and set `provider: local`.  
* **Hook up Jira.** Enable the *ticket-agent* to auto-create tickets on failures.  
* **Scale out.** Apply the Kubernetes manifests in `kubernetes/`.  
* **PRs welcome!** See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

Happy automating! 🚀