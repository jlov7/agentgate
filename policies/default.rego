package agentgate

import future.keywords.if
import future.keywords.in

default decision = {"action": "DENY", "reason": "No matching rule"}

# Read-only tools allowed
decision = {
    "action": "ALLOW",
    "reason": "Read-only tool",
    "matched_rule": "read_only_tools",
    "allowed_scope": "read",
    "is_write_action": false
} if {
    input.tool_name in data.read_only_tools
}

# Write tools require approval
decision = {
    "action": "REQUIRE_APPROVAL",
    "reason": "Write action requires human approval",
    "matched_rule": "write_requires_approval",
    "is_write_action": true
} if {
    input.tool_name in data.write_tools
    not input.has_approval_token
}

# Write tools with valid approval
decision = {
    "action": "ALLOW",
    "reason": "Write action approved",
    "matched_rule": "write_with_approval",
    "allowed_scope": "write",
    "is_write_action": true
} if {
    input.tool_name in data.write_tools
    input.has_approval_token
    # In production, validate the token properly
}

# Deny unknown tools
decision = {
    "action": "DENY",
    "reason": "Tool not in allowlist",
    "matched_rule": "unknown_tool"
} if {
    not input.tool_name in data.all_known_tools
}
