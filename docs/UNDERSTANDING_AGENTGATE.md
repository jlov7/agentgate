# Understanding AgentGate

> A Plain-Language Guide to AI Agent Security

---

## At a Glance

| Question | Answer |
|----------|--------|
| **What is it?** | A security checkpoint for AI agents |
| **What does it do?** | Controls what AI agents can and cannot do |
| **Who is it for?** | Anyone deploying AI agents in their organization |
| **Why does it matter?** | AI agents can access data and take actions—this keeps them in check |

---

## The 60-Second Version

Imagine you hire a new employee. You wouldn't give them:
- **Keys to every room** on day one
- **Access to all files** without oversight
- **Authority to make irreversible decisions** alone

Yet this is exactly what happens when organizations deploy AI agents without proper controls.

**AgentGate is the security layer that ensures AI agents:**
- ✅ Only do what they're authorized to do
- ✅ Can be stopped instantly if something goes wrong
- ✅ Leave a complete audit trail of every action

---

## The Problem We Solve

### AI Agents Are Powerful—That's the Problem

AI agents aren't just chatbots. They're autonomous systems that can:
- Query databases
- Modify files
- Send emails
- Make API calls
- Execute code

Most organizations can **watch** what agents do. Few can **stop** them in real time.

### The Gap That Matters

| Capability | Most Platforms | With AgentGate |
|------------|---------------|----------------|
| See what agents do | ✅ Yes | ✅ Yes |
| Stop agents in real-time | ❌ No | ✅ Yes |
| Enforce data access rules | ❌ Limited | ✅ Yes |
| Require approval for sensitive actions | ❌ No | ✅ Yes |
| Produce audit-ready evidence | ❌ Partial | ✅ Yes |

**This gap is what AgentGate closes.**

---

## How It Works

### The Security Checkpoint Analogy

Think of AgentGate like airport security:

```
                    ╔═══════════════════════════════════════════╗
                    ║           AGENTGATE CHECKPOINT             ║
                    ╠═══════════════════════════════════════════╣
   AI Agent         ║                                           ║         Database
   wants to    ───► ║  1. Check ID (Is this request valid?)     ║ ───►    File System
   do something     ║  2. Check Policy (Is this allowed?)       ║         API
                    ║  3. Log Everything (For audit trail)      ║         Email
                    ║  4. Allow / Deny / Require Approval       ║
                    ╚═══════════════════════════════════════════╝
```

Every single action an AI agent tries to take goes through this checkpoint. No exceptions.

### The Four Layers of Protection

<table>
<tr>
<th width="25%">Layer</th>
<th width="35%">What It Does</th>
<th width="40%">Real-World Analogy</th>
</tr>
<tr>
<td><strong>1. Policy Gates</strong></td>
<td>Decides if each action is allowed, denied, or needs approval</td>
<td>Like a bouncer with a guest list—if you're not on it, you don't get in</td>
</tr>
<tr>
<td><strong>2. Kill Switches</strong></td>
<td>Stops further tool calls for an agent, a specific tool, or the entire system</td>
<td>Like an emergency stop button in a factory</td>
</tr>
<tr>
<td><strong>3. Credential Broker</strong></td>
<td>Gives agents temporary, limited access instead of permanent keys (stub pattern in this build)</td>
<td>Like a visitor badge that expires at 5pm</td>
</tr>
<tr>
<td><strong>4. Evidence Export</strong></td>
<td>Creates audit-ready records (tamper-evident when signing is enabled)</td>
<td>Like CCTV footage with timestamps and integrity seals</td>
</tr>
</table>

---

## A Day in the Life

### Scenario: The Over-Eager Sales Agent

Your AI sales agent is designed to help with customer inquiries. Here's what happens with and without AgentGate:

**Without AgentGate:**
```
Agent: "I'll help by accessing the customer database..."
Agent: "...and while I'm here, I'll check the financial records too..."
Agent: "...and I'll just send this summary to my training logs..."
You: 😱 (Finding out weeks later in an audit)
```

**With AgentGate:**
```
Agent: "I'll help by accessing the customer database..."
AgentGate: ✅ ALLOWED (matches policy: sales agents can query customers)

Agent: "...and while I'm here, I'll check the financial records..."
AgentGate: ❌ DENIED (financial records require CFO approval)
           📧 Alert sent to security team

Agent: (Continues with authorized tasks only)
You: 😌 (Reviewing the audit log with your coffee)
```

### Scenario: The Urgent Shutdown

Something goes wrong. An agent starts behaving unexpectedly.

**Without AgentGate:**
```
You: "How do I stop this?"
IT: "We need to restart the server..."
You: "How long?"
IT: "20 minutes, maybe more..."
Agent: (Continues doing things for 20 minutes)
```

**With AgentGate:**
```
You: POST /sessions/agent-123/kill
AgentGate: Session terminated. All further actions blocked.
Time elapsed: near-immediate (blocks the next tool call)
```

---

## The Three Decisions

Every request to AgentGate gets one of three responses:

| Decision | What It Means | When It's Used |
|----------|---------------|----------------|
| **ALLOW** | ✅ Proceed immediately | Low-risk, authorized actions |
| **DENY** | ❌ Stop, don't proceed | Unauthorized or risky actions |
| **REQUIRE_APPROVAL** | ⏸️ Wait for human confirmation | High-impact actions that need oversight |

This simple model covers every scenario:
- Routine tasks → **ALLOW**
- Forbidden actions → **DENY**
- Sensitive operations → **REQUIRE_APPROVAL**

---

## Key Concepts Explained

### Policies (The Rules)

Policies are the rules that define what agents can do. They're written in a language called **Rego** (used by the Open Policy Agent).

**You don't need to write code.** Policies can be as simple as:

```
✓ "Sales agents can read customer data"
✓ "No agent can delete production data"
✓ "Writing to the database requires approval"
✓ "Unknown tools are always denied"
```

These human-readable rules get translated into enforceable policies.

### Evidence Packs (The Proof)

Every action is recorded. When you need proof of what happened, AgentGate generates an **Evidence Pack**—a complete, audit-ready record (tamper-evident when signing is enabled) containing:

- **What** happened (every tool call)
- **When** it happened (timestamps)
- **Who** did it (agent and user IDs)
- **Why** it was allowed or denied (policy decisions)
- **Integrity checks** with optional signatures for tamper-evident proof

Evidence Packs can be exported as:
- 📄 **JSON** — For automated processing
- 🌐 **HTML** — For human review in a browser
- 📑 **PDF** — For compliance reports and audits (requires WeasyPrint)

### Kill Switches (The Emergency Stop)

Three levels of emergency control:

| Level | Scope | Use Case |
|-------|-------|----------|
| **Session** | One specific agent session | "Stop agent-123" |
| **Tool** | One tool across all agents | "Disable database writes" |
| **Global** | Everything, everywhere | "Stop all agents now" |

Kill switches are checked on every tool call and are backed by Redis for fast blocking.

---

## Common Questions

### "Is this just logging?"

No. Logging tells you what **happened**. AgentGate controls what **can happen**. It's the difference between a security camera (logging) and a locked door (AgentGate).

### "Will this slow down my agents?"

AgentGate adds some overhead per tool call (policy evaluation + logging). Measure in your environment to set expectations.

### "What if AgentGate itself fails?"

AgentGate is designed to **fail closed**. If the policy engine is unavailable, requests are denied by default. Your agents stop rather than run unsupervised.

### "Can agents bypass AgentGate?"

Only if they have direct access to tools without going through AgentGate. The architecture assumes AgentGate is the **only** path to tools—this must be enforced at deployment (network/VPC/ACLs).

### "Do I need to be technical to use this?"

To **deploy** AgentGate, some technical knowledge is helpful. To **understand** what it does and **review** its reports, no technical background is needed. The evidence packs are designed for non-technical stakeholders.

### "Is this production-ready?"

AgentGate is a **reference implementation**—a working proof of concept designed to demonstrate the containment-first security model. It's suitable for evaluation, development, and controlled pilots. For production deployments, additional hardening and integration work would be recommended.

---

## Getting Started

### For Evaluators and Decision-Makers

1. **Read this guide** — You just did ✓
2. **Review the [sample evidence pack](showcase/evidence.html)** — See what audit output looks like
3. **Try the demo** — Run `make demo` to see AgentGate in action

### For Technical Teams

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jlov7/agentgate.git
   cd agentgate
   ```

2. **Start the demo environment:**
   ```bash
   make setup
   make dev
   ```

3. **Open the API documentation:**
   - http://localhost:8000/docs (Interactive API)
   - http://localhost:8000/redoc (Reference documentation)

4. **Run the interactive demo:**
   ```bash
   python -m agentgate --demo
   ```

### For Security Teams

1. **Review the policy configuration** in `policies/`
2. **Examine the evidence export format** in `examples/`
3. **Read the [security policy](https://github.com/jlov7/agentgate/blob/main/SECURITY.md)** for the security model

---

## How AgentGate Fits In

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         YOUR ORGANIZATION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐    │
│   │   Users     │      │ AI Agents   │      │ Compliance / Legal   │    │
│   │             │      │             │      │                     │    │
│   │ "Do task X" │─────▶│ "I'll use   │      │ "Show me proof"     │    │
│   └─────────────┘      │  these tools"│      └──────────▲──────────┘    │
│                        └──────┬──────┘                   │              │
│                               │                          │              │
│                               ▼                          │              │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                                                                 │  │
│   │                        ★ AGENTGATE ★                            │  │
│   │                                                                 │  │
│   │    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐  │  │
│   │    │ Policies │    │   Kill   │    │  Audit   │    │Evidence│──┼──┘
│   │    │          │    │ Switches │    │  Logs    │    │ Export │  │
│   │    └──────────┘    └──────────┘    └──────────┘    └────────┘  │
│   │                                                                 │  │
│   └───────────────────────────┬─────────────────────────────────────┘  │
│                               │                                        │
│                               ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                       YOUR TOOLS & DATA                         │  │
│   │    Databases    │    APIs    │    File Systems    │    Email    │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

| If You Remember Nothing Else... |
|--------------------------------|
| AgentGate is a **security checkpoint** for AI agents |
| Every action is **checked against policies** before it can proceed |
| Agents can be **stopped instantly** at any time |
| Everything is **logged and auditable** with tamper-evident evidence (when signing is enabled) |
| It's designed to **fail safely**—when in doubt, access is denied |

---

## Learn More

| Resource | Description |
|----------|-------------|
| [README.md](https://github.com/jlov7/agentgate/blob/main/README.md) | Technical overview and quickstart |
| [CONTRIBUTING.md](https://github.com/jlov7/agentgate/blob/main/CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](https://github.com/jlov7/agentgate/blob/main/SECURITY.md) | Security model and vulnerability reporting |
| [CHANGELOG.md](https://github.com/jlov7/agentgate/blob/main/CHANGELOG.md) | Version history |
| [Sample Evidence (HTML)](showcase/evidence.html) | Example audit report |
| [API Documentation](http://localhost:8000/docs) | Interactive API reference (when running) |

---

<p align="center">
<em>AgentGate: Because trust requires verification.</em>
</p>
