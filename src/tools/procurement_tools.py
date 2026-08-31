"""Procurement agentic tools with human-in-the-loop action queue."""

from __future__ import annotations
from dotenv import load_dotenv
import os

import json
from typing import Any, Callable

from langchain.tools import tool

from src.data_logic.action_queue import execute_action, queue_action, should_auto_execute
from src.data_logic.audit_log import log_event
from src.data_logic.deal_memory import compile_deal_memory, get_deal_memory, list_suppliers
load_dotenv()


CLARA_FROM_EMAIL = os.getenv("CLARA_FROM_EMAIL")
_UNKNOWN_EMAIL_TOKENS = {"unknown", "tbd", "n/a", "na", "none", "not provided", "missing"}


def _split_csv_values(raw_value: str) -> list[str]:
    return [value.strip() for value in raw_value.split(",") if value and value.strip()]


def _is_valid_email(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized or normalized in _UNKNOWN_EMAIL_TOKENS or " " in normalized:
        return False
    local_part, at, domain_part = normalized.partition("@")
    return bool(at and local_part and "." in domain_part and not domain_part.startswith(".") and not domain_part.endswith("."))


def _log_tool_call(
    audit_callback: Callable | None,
    tool_name: str,
    args: dict,
    result: Any,
    user_id: str | None,
    chat_id: str | None,
    document_refs: list[str] | None = None,
):
    if audit_callback:
        audit_callback(tool_name, args, result, document_refs)
    else:
        log_event(
            event_type="tool_invocation",
            user_id=user_id,
            chat_id=chat_id,
            tool_name=tool_name,
            details={"args": args, "result_preview": str(result)[:500]},
            document_refs=document_refs or [],
        )


def _queue_or_execute(
    action_type: str,
    payload: dict,
    reasoning: str,
    source_documents: list[str],
    user_id: str | None,
    chat_id: str | None,
    authority_tier: str | None = None,
) -> str:
    if not user_id:
        return json.dumps({"error": "User context required for this action"})

    action = queue_action(
        user_id=user_id,
        action_type=action_type,
        payload=payload,
        reasoning=reasoning,
        source_documents=source_documents,
        chat_id=chat_id,
        authority_tier=authority_tier,
    )

    log_event(
        event_type="action_queued" if action["status"] == "pending" else "action_auto_executed",
        user_id=user_id,
        chat_id=chat_id,
        tool_name=action_type,
        details={"action_id": action["id"], "payload": payload},
        document_refs=source_documents,
        reasoning=reasoning,
    )

    if should_auto_execute(action["authority_tier"]):
        exec_result = execute_action(action)
        return json.dumps({
            "status": "executed",
            "action_id": action["id"],
            "authority_tier": action["authority_tier"],
            "reasoning": reasoning,
            "result": exec_result,
        })

    return json.dumps({
        "status": "pending_approval",
        "action_id": action["id"],
        "action_type": action_type,
        "authority_tier": action["authority_tier"],
        "reasoning": reasoning,
        "source_documents": source_documents,
        "message": (
            f"This action requires {'manager sign-off' if action['authority_tier'] == 'binding' else 'your confirmation'} "
            f"before execution. Action ID: {action['id']}"
        ),
        "payload_preview": payload,
    })


def create_procurement_tools(
    collection=None,
    user_id: str | None = None,
    chat_id: str | None = None,
    audit_callback: Callable | None = None,
) -> list:
    """Create Deal Memory and agentic procurement tools."""

    @tool
    def deal_memory_tool(supplier_name: str) -> str:
        """Build or retrieve a Deal Memory dossier for an active supplier.

        Compiles: contract summary, payment history, dispute log,
        compliance status, and relationship health score (0-100).
        Use when the user asks about a supplier relationship, vendor history,
        or before initiating sourcing/negotiation with a known supplier.
        """
        dossier = compile_deal_memory(
            user_id=user_id,
            supplier_name=supplier_name,
            collection=collection,
            chat_id=chat_id,
        )
        _log_tool_call(
            audit_callback, "deal_memory_tool", {"supplier_name": supplier_name},
            dossier, user_id, chat_id, dossier.get("source_documents"),
        )
        return json.dumps(dossier, indent=2)

    @tool
    def list_active_suppliers() -> str:
        """List all active suppliers in the supplier database.
        Use to find pre-qualified vendors for sourcing events."""
        suppliers = list_suppliers(user_id) if user_id else []
        _log_tool_call(audit_callback, "list_active_suppliers", {}, suppliers, user_id, chat_id)
        return json.dumps(suppliers, indent=2) if suppliers else "No active suppliers found."

    @tool
    def draft_email_tool(
        recipients: str,
        subject: str,
        body: str,
        reasoning: str,
        source_documents: str = "",
    ) -> str:
        """Draft an email to suppliers or stakeholders. BINDING action — requires manager sign-off before sending.

        Args:
            recipients: Comma-separated email addresses or vendor names
            subject: Email subject line
            body: Full email body text
            reasoning: Why this email should be sent, referencing supporting documents
            source_documents: Comma-separated list of source document filenames
        """
        docs = [d.strip() for d in source_documents.split(",") if d.strip()]
        recipient_values = _split_csv_values(recipients)
        invalid_recipients = [value for value in recipient_values if not _is_valid_email(value)]

        if not recipient_values or invalid_recipients:
            return json.dumps({
                "status": "recipient_email_required",
                "message": (
                    "Please provide the recipient email address(es) before I queue this email. "
                    "I can only proceed once all recipients are valid email addresses."
                ),
                "invalid_recipients": invalid_recipients,
            })

        payload = {
            "from_email": CLARA_FROM_EMAIL,
            "recipients": ", ".join(recipient_values),
            "subject": subject,
            "body": body,
        }
        return _queue_or_execute("draft_email", payload, reasoning, docs, user_id, chat_id)

    @tool
    def send_rfp_tool(
        vendors: str,
        vendor_emails: str,
        rfp_title: str,
        requirements: str,
        deadline: str,
        budget: str,
        reasoning: str,
        source_documents: str = "",
    ) -> str:
        """Draft and queue RFP invitations to pre-qualified vendors. BINDING action — requires manager sign-off.

        Args:
            vendors: Comma-separated vendor names
            vendor_emails: Comma-separated recipient email addresses aligned to vendors
            rfp_title: Title of the sourcing event
            requirements: Key requirements summary
            deadline: Response deadline
            budget: Budget amount and currency
            reasoning: Justification for vendor selection and RFP scope
            source_documents: Comma-separated source document filenames
        """
        vendor_list = [v.strip() for v in vendors.split(",") if v.strip()]
        recipient_emails = _split_csv_values(vendor_emails)
        invalid_recipients = [value for value in recipient_emails if not _is_valid_email(value)]

        if not recipient_emails or invalid_recipients:
            return json.dumps({
                "status": "recipient_email_required",
                "message": (
                    "Please provide the vendor recipient email address(es) before I queue this RFP. "
                    "I can only proceed once all recipients are valid email addresses."
                ),
                "invalid_recipients": invalid_recipients,
            })

        if vendor_list and len(vendor_list) != len(recipient_emails):
            return json.dumps({
                "status": "recipient_email_mapping_required",
                "message": (
                    "Please provide one vendor email per vendor in the same order so I can queue the RFP correctly."
                ),
            })

        docs = [d.strip() for d in source_documents.split(",") if d.strip()]
        payload = {
            "from_email": CLARA_FROM_EMAIL,
            "vendors": vendor_list,
            "vendor_emails": recipient_emails,
            "rfp_title": rfp_title,
            "requirements": requirements,
            "deadline": deadline,
            "budget": budget,
        }
        return _queue_or_execute("send_rfp", payload, reasoning, docs, user_id, chat_id)

    @tool
    def create_spreadsheet_tool(
        title: str,
        columns: str,
        criteria_weights: str,
        reasoning: str,
        source_documents: str = "",
    ) -> str:
        """Create a bid evaluation scorecard or comparison matrix spreadsheet.

        Args:
            title: Spreadsheet title (e.g. 'Laptop Bid Evaluation Scorecard')
            columns: Comma-separated column headers (e.g. 'Vendor,Price,Warranty,Delivery,Sustainability,Total Score')
            criteria_weights: JSON string of weights (e.g. '{"price": 40, "warranty": 20, "delivery": 20, "sustainability": 20}')
            reasoning: Why this scorecard structure was chosen
            source_documents: Comma-separated source document filenames
        """
        docs = [d.strip() for d in source_documents.split(",") if d.strip()]
        try:
            weights = json.loads(criteria_weights) if criteria_weights else {}
        except json.JSONDecodeError:
            weights = {"price": 40, "warranty": 20, "delivery": 20, "sustainability": 20}
        payload = {
            "title": title,
            "columns": [c.strip() for c in columns.split(",") if c.strip()],
            "criteria_weights": weights,
        }
        return _queue_or_execute("create_spreadsheet", payload, reasoning, docs, user_id, chat_id, "standard")

    @tool
    def generate_pdf_memo_tool(
        title: str,
        sections: str,
        reasoning: str,
        source_documents: str = "",
    ) -> str:
        """Generate an executive approval memo PDF with budget justification, market analysis, and risk assessment.

        Args:
            title: Memo title (e.g. 'Executive Approval Memo - Laptop Procurement')
            sections: JSON string of section name to content mapping
            reasoning: Why this memo is needed and what decision it supports
            source_documents: Comma-separated source document filenames
        """
        docs = [d.strip() for d in source_documents.split(",") if d.strip()]
        try:
            section_data = json.loads(sections) if sections else {}
        except json.JSONDecodeError:
            section_data = {"summary": sections}
        payload = {"title": title, "sections": section_data}
        return _queue_or_execute("generate_pdf_memo", payload, reasoning, docs, user_id, chat_id, "standard")

    @tool
    def schedule_calendar_event_tool(
        title: str,
        datetime_str: str,
        attendees: str,
        description: str,
        reasoning: str,
    ) -> str:
        """Schedule a stakeholder review meeting or procurement milestone on the calendar.

        Args:
            title: Meeting title
            datetime_str: Date and time (e.g. 'Wednesday 3:00 PM')
            attendees: Comma-separated attendee names or emails
            description: Meeting agenda or purpose
            reasoning: Why this meeting is scheduled at this time
        """
        payload = {
            "title": title,
            "datetime": datetime_str,
            "attendees": [a.strip() for a in attendees.split(",") if a.strip()],
            "description": description,
        }
        return _queue_or_execute("schedule_calendar_event", payload, reasoning, [], user_id, chat_id, "standard")

    @tool
    def present_for_review_tool(
        package_summary: str,
        items: str,
        reasoning: str,
    ) -> str:
        """Present a completed procurement package to the user for review before any external actions.

        Always call this as the final step in multi-tool sourcing workflows.

        Args:
            package_summary: Brief summary of the complete package
            items: Comma-separated list of deliverables included (e.g. 'RFP drafts, scorecard, approval memo, calendar invite')
            reasoning: Overview of the workflow completed and recommended next steps
        """
        item_list = [i.strip() for i in items.split(",") if i.strip()]
        payload = {"summary": package_summary, "items": item_list}
        return _queue_or_execute("present_for_review", payload, reasoning, [], user_id, chat_id, "routine")

    return [
        deal_memory_tool,
        list_active_suppliers,
        draft_email_tool,
        send_rfp_tool,
        create_spreadsheet_tool,
        generate_pdf_memo_tool,
        schedule_calendar_event_tool,
        present_for_review_tool,
    ]
