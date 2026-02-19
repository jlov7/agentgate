package agentgate_test

import data.agentgate

test_read_only_tool_allowed if {
	decision := agentgate.decision with input as {
		"tool_name": "db_query",
		"has_approval_token": false,
	}
		with data.read_only_tools as ["db_query"] with data.write_tools as ["db_update"] with data.all_known_tools as ["db_query", "db_update"]
	decision.action == "ALLOW"
	decision.matched_rule == "read_only_tools"
}

test_write_requires_approval if {
	decision := agentgate.decision with input as {
		"tool_name": "db_update",
		"has_approval_token": false,
	}
		with data.read_only_tools as ["db_query"] with data.write_tools as ["db_update"] with data.all_known_tools as ["db_query", "db_update"]
	decision.action == "REQUIRE_APPROVAL"
	decision.matched_rule == "write_requires_approval"
}

test_write_with_approval_allowed if {
	decision := agentgate.decision with input as {
		"tool_name": "db_update",
		"has_approval_token": true,
	}
		with data.read_only_tools as ["db_query"] with data.write_tools as ["db_update"] with data.all_known_tools as ["db_query", "db_update"]
	decision.action == "ALLOW"
	decision.matched_rule == "write_with_approval"
}

test_unknown_tool_denied if {
	decision := agentgate.decision with input as {
		"tool_name": "unknown_tool",
		"has_approval_token": false,
	}
		with data.read_only_tools as ["db_query"] with data.write_tools as ["db_update"] with data.all_known_tools as ["db_query", "db_update"]
	decision.action == "DENY"
	decision.matched_rule == "unknown_tool"
}

test_known_tool_without_rule_uses_default_deny if {
	decision := agentgate.decision with input as {
		"tool_name": "known_without_category",
		"has_approval_token": false,
	}
		with data.read_only_tools as ["db_query"] with data.write_tools as ["db_update"] with data.all_known_tools as ["db_query", "db_update", "known_without_category"]
	decision.action == "DENY"
	decision.reason == "No matching rule"
}
