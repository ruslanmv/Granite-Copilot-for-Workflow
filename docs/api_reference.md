# API Reference

This document details the HTTP endpoints and NATS subjects used by Granite Copilot for Workflow.

---

## HTTP REST Endpoints

### 1. `POST /api/workflows`
Create or update a workflow definition (YAML).

- **Content-Type:** `application/x-yaml`
- **Request Body:** Full workflow YAML (see examples/nightly_build.yaml).
- **Responses:**
  - `201 Created`  
    ```json
    {
      "workflowId": "string",
      "message": "Workflow created"
    }
    ```
  - `200 OK` (if replacing existing)
  - `400 Bad Request` (invalid YAML or schema)

### 2. `GET /api/workflows`
List all registered workflows.

- **Responses:**
  - `200 OK`  
    ```json
    [
      { "workflowId": "string", "name": "string", "schedule": "string" },
      …
    ]
    ```

### 3. `GET /api/workflows/{workflowId}`
Retrieve a specific workflow definition.

- **Responses:**
  - `200 OK`  
    ```yaml
    # full YAML definition
    ```
  - `404 Not Found`

### 4. `POST /api/workflows/{workflowId}/runs`
Trigger a manual run of a workflow.

- **Request Body (optional JSON overrides):**
  ```json
  { "overrides": { /* partial DAG overrides */ } }
