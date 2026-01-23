# AgentGate E2E Test Plan

## 1. Documentation & Health (Happy Paths)
**Seed:** `seed.spec.ts`

### 1.1 Load Swagger UI
**Steps:**
1. Open `/docs`
2. Wait for the Swagger UI container to render
3. Confirm the API title includes "AgentGate"

**Expected:** Swagger UI renders and displays the API title.

### 1.2 Load ReDoc
**Steps:**
1. Open `/redoc`
2. Wait for ReDoc content to render
3. Confirm the page header includes "AgentGate"

**Expected:** ReDoc renders with the API title.

### 1.3 Health Check Returns OK
**Steps:**
1. Send `GET /health`
2. Confirm status is `200`
3. Verify `status` is `ok`, `opa` is `true`, `redis` is `true`

**Expected:** Health endpoint reports all dependencies healthy.

## 2. Core Tool Flows (Happy Paths)
**Seed:** `seed.spec.ts`

### 2.1 List Allowed Tools
**Steps:**
1. Send `GET /tools/list?session_id=e2e-happy-tools`
2. Confirm status is `200`
3. Verify `db_query` appears in the tool list

**Expected:** Policy allowlist returns expected read-only tools.

### 2.2 Allowed Read-Only Tool Call
**Steps:**
1. Send `POST /tools/call` for `db_query`
2. Provide a `session_id` and query arguments
3. Confirm the response indicates `success: true`

**Expected:** Read-only tool calls are allowed and return a stub result.

### 2.3 Approved Write Tool Call
**Steps:**
1. Send `POST /tools/call` for `db_update` with `approval_token=approved`
2. Provide a `session_id`
3. Confirm the response indicates `success: true`

**Expected:** Approved write tool calls succeed.

## 3. Sessions & Evidence (Happy Paths)
**Seed:** `seed.spec.ts`

### 3.1 Session Appears After Tool Call
**Steps:**
1. Send `POST /tools/call` for `db_query` with a new `session_id`
2. Send `GET /sessions`
3. Verify the session id appears in the list

**Expected:** Session registry includes the new session.

### 3.2 Export Evidence Pack (JSON)
**Steps:**
1. Send `GET /sessions/{session_id}/evidence`
2. Confirm status is `200`
3. Verify `metadata.session_id` matches the session

**Expected:** Evidence pack is returned in JSON format.

## 4. Negative & Edge Scenarios
**Seed:** `seed.spec.ts`

### 4.1 Missing Required Fields (422)
**Steps:**
1. Send `POST /tools/call` with an empty JSON body

**Expected:** Request fails with HTTP 422 validation error.

### 4.2 Invalid Tool Name Characters
**Steps:**
1. Send `POST /tools/call` with `tool_name` containing `/` or spaces

**Expected:** Response indicates denial due to invalid tool name.

### 4.3 Unknown Tool Denied
**Steps:**
1. Send `POST /tools/call` with `tool_name=unknown_tool`

**Expected:** Response indicates the tool is not in the allowlist.

### 4.4 Write Tool Without Approval
**Steps:**
1. Send `POST /tools/call` for `db_update` without `approval_token`

**Expected:** Response indicates approval is required.

### 4.5 Rate Limit Exceeded
**Steps:**
1. Send 11 calls to `rate_limited_tool` in the same session

**Expected:** At least one response indicates rate limit exceeded.

### 4.6 Request Body Too Large (413)
**Steps:**
1. Send `POST /tools/call` with a payload larger than 1MB

**Expected:** Request rejected with HTTP 413.

### 4.7 Killed Session Blocks Tool Calls (Expired Session)
**Steps:**
1. Send `POST /sessions/{id}/kill`
2. Send `POST /tools/call` using the killed `session_id`

**Expected:** Tool call is denied due to kill switch.

### 4.8 Global Pause Blocks Tool Calls
**Steps:**
1. Send `POST /system/pause`
2. Send `POST /tools/call` with any tool
3. Send `POST /system/resume`

**Expected:** Tool call is denied while paused and system can resume.

### 4.9 Invalid Admin API Key
**Steps:**
1. Send `POST /admin/policies/reload` with wrong `X-API-Key`

**Expected:** Request rejected with HTTP 403.

### 4.10 Network Failure to API Host
**Steps:**
1. Send `GET /health` using an invalid base URL

**Expected:** Network error is surfaced to the client.
