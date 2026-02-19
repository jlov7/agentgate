"""Approval workflow engine with multi-step, expiry, and delegation support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any
from uuid import uuid4

from agentgate.models import ToolCallRequest

WORKFLOW_TOKEN_PREFIX = "wf:"  # noqa: S105  # nosec B105


def _normalize_identity(value: str) -> str:
    return value.strip().lower()


@dataclass
class ApprovalWorkflow:
    workflow_id: str
    session_id: str
    tool_name: str
    required_steps: int
    required_approvers: list[str]
    requested_by: str | None
    created_at: datetime
    expires_at: datetime
    approvals: set[str] = field(default_factory=set)
    delegations: dict[str, str] = field(default_factory=dict)
    updated_at: datetime | None = None


class ApprovalWorkflowEngine:
    """In-memory workflow engine for approval token lifecycle management."""

    def __init__(self) -> None:
        self._workflows: dict[str, ApprovalWorkflow] = {}
        self._lock = RLock()

    def create_workflow(
        self,
        *,
        session_id: str,
        tool_name: str,
        required_steps: int,
        required_approvers: list[str],
        requested_by: str | None,
        expires_in_seconds: int | None,
        expires_at: datetime | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        normalized_required = self._normalize_required_approvers(required_approvers)
        if normalized_required and required_steps > len(normalized_required):
            raise ValueError("required_steps cannot exceed number of required_approvers")

        effective_expiry = self._compute_expiry(
            now=now,
            expires_in_seconds=expires_in_seconds,
            expires_at=expires_at,
        )

        workflow_id = str(uuid4())
        workflow = ApprovalWorkflow(
            workflow_id=workflow_id,
            session_id=session_id,
            tool_name=tool_name,
            required_steps=required_steps,
            required_approvers=normalized_required,
            requested_by=requested_by.strip() if isinstance(requested_by, str) else None,
            created_at=now,
            expires_at=effective_expiry,
        )

        with self._lock:
            self._workflows[workflow_id] = workflow
        return self._serialize(workflow)

    def approve(self, workflow_id: str, approver_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        approver = _normalize_identity(approver_id)
        with self._lock:
            workflow = self._require_workflow(workflow_id)
            if self._is_expired(workflow, now):
                raise ValueError("workflow expired")
            slot = self._approval_slot_for_approver(workflow, approver)
            if slot is None:
                raise ValueError("approver is not authorized for this workflow")
            workflow.approvals.add(slot)
            workflow.updated_at = now
            return self._serialize(workflow)

    def delegate(
        self,
        workflow_id: str,
        *,
        from_approver: str,
        to_approver: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        from_identity = _normalize_identity(from_approver)
        to_identity = _normalize_identity(to_approver)
        if from_identity == to_identity:
            raise ValueError("delegate target must differ from source approver")

        with self._lock:
            workflow = self._require_workflow(workflow_id)
            if self._is_expired(workflow, now):
                raise ValueError("workflow expired")
            if not workflow.required_approvers:
                raise ValueError("delegation requires explicit required_approvers")
            if from_identity not in workflow.required_approvers:
                raise ValueError("from_approver is not part of workflow required approvers")
            if from_identity in workflow.approvals:
                raise ValueError("cannot delegate an already-approved slot")

            stale = [
                delegate
                for delegate, source in workflow.delegations.items()
                if source == from_identity
            ]
            for delegate in stale:
                workflow.delegations.pop(delegate, None)
            workflow.delegations[to_identity] = from_identity
            workflow.updated_at = now
            return self._serialize(workflow)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        with self._lock:
            workflow = self._require_workflow(workflow_id)
            return self._serialize(workflow)

    def verify_token(self, token: str, request: ToolCallRequest | None = None) -> bool:
        if not isinstance(token, str) or not token.startswith(WORKFLOW_TOKEN_PREFIX):
            return False
        workflow_id = token[len(WORKFLOW_TOKEN_PREFIX) :].strip()
        if not workflow_id:
            return False

        now = datetime.now(UTC)
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                return False
            if self._is_expired(workflow, now):
                return False
            if request is not None:
                if workflow.session_id != request.session_id:
                    return False
                if workflow.tool_name != request.tool_name:
                    return False
            return self._is_approved(workflow)

    def _require_workflow(self, workflow_id: str) -> ApprovalWorkflow:
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError("workflow not found")
        return workflow

    @staticmethod
    def _normalize_required_approvers(required_approvers: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in required_approvers:
            if not isinstance(raw, str):
                continue
            identity = _normalize_identity(raw)
            if not identity or identity in seen:
                continue
            seen.add(identity)
            normalized.append(identity)
        return normalized

    @staticmethod
    def _compute_expiry(
        *,
        now: datetime,
        expires_in_seconds: int | None,
        expires_at: datetime | None,
    ) -> datetime:
        if expires_at is not None:
            if expires_at.tzinfo is None:
                return expires_at.replace(tzinfo=UTC)
            return expires_at.astimezone(UTC)
        ttl_seconds = 900 if expires_in_seconds is None else max(1, expires_in_seconds)
        return now + timedelta(seconds=ttl_seconds)

    @staticmethod
    def _is_expired(workflow: ApprovalWorkflow, now: datetime) -> bool:
        return now >= workflow.expires_at

    @staticmethod
    def _is_approved(workflow: ApprovalWorkflow) -> bool:
        return len(workflow.approvals) >= workflow.required_steps

    @staticmethod
    def _approval_slot_for_approver(workflow: ApprovalWorkflow, approver: str) -> str | None:
        if workflow.required_approvers:
            if approver in workflow.required_approvers:
                return approver
            delegated_slot = workflow.delegations.get(approver)
            if delegated_slot in workflow.required_approvers:
                return delegated_slot
            return None
        return approver

    def _serialize(self, workflow: ApprovalWorkflow) -> dict[str, Any]:
        now = datetime.now(UTC)
        if self._is_approved(workflow):
            status = "approved"
        elif self._is_expired(workflow, now):
            status = "expired"
        else:
            status = "pending"

        return {
            "workflow_id": workflow.workflow_id,
            "approval_token": f"{WORKFLOW_TOKEN_PREFIX}{workflow.workflow_id}",
            "session_id": workflow.session_id,
            "tool_name": workflow.tool_name,
            "required_steps": workflow.required_steps,
            "required_approvers": workflow.required_approvers,
            "approvals": sorted(workflow.approvals),
            "delegations": dict(sorted(workflow.delegations.items())),
            "requested_by": workflow.requested_by,
            "status": status,
            "created_at": workflow.created_at.isoformat(),
            "expires_at": workflow.expires_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        }
