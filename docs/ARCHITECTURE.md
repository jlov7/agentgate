# AgentGate Architecture

## Data Flow
```mermaid
flowchart LR
  A[Agent Runtime] -->|MCP tool call| B[AgentGate Gateway]
  B --> C[Policy Gate OPA Rego]
  B --> D[Kill Switch Redis]
  B --> E[Credential Broker]
  B --> F[Trace Store append-only]
  B --> G[Metrics endpoint]
  B --> H[Webhook Alerts]
  B --> I[MCP Tool Servers]
```

## Policy Decision Sequence
```mermaid
sequenceDiagram
  autonumber
  participant Agent
  participant Gateway
  participant Policy as Policy Gate
  participant Trace as Trace Store
  participant Tool as Tool Server

  Agent->>Gateway: POST /tools/call
  Gateway->>Policy: Evaluate policy
  Policy-->>Gateway: ALLOW / DENY / REQUIRE_APPROVAL
  Gateway->>Trace: Append decision + context
  alt ALLOW
    Gateway->>Tool: Execute tool call
    Tool-->>Gateway: Result
  else REQUIRE_APPROVAL
    Gateway-->>Agent: Pending approval
  else DENY
    Gateway-->>Agent: Denied
  end
  Gateway->>Trace: Append outcome
  Gateway-->>Agent: Response
```

## Slide-Ready Diagrams
- `docs/assets/architecture-flow.svg`
- `docs/assets/policy-sequence.svg`

Regenerate SVGs with `scripts/render_diagrams.sh`.
