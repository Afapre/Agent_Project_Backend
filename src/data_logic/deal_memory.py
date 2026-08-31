"""Deal Memory: compile supplier dossiers from documents and stored records."""

from __future__ import annotations

import re
import uuid
from typing import Any

from src.data_logic.postgres import SessionLocal
from src.data_logic.retrieval_scope import query_scope_matches
from src.models.deal_memory_model import DealMemory
from src.models.supplier_model import Supplier


def _serialize_supplier(supplier: Supplier) -> dict:
    return {
        "id": str(supplier.id),
        "name": supplier.name,
        "status": supplier.status,
        "contact_email": supplier.contact_email,
        "category": supplier.category,
        "metadata": supplier.metadata_json or {},
    }


def _serialize_deal_memory(memory: DealMemory, supplier_name: str) -> dict:
    return {
        "id": str(memory.id),
        "supplier_id": str(memory.supplier_id),
        "supplier_name": supplier_name,
        "contract_summary": memory.contract_summary,
        "payment_history": memory.payment_history or [],
        "dispute_log": memory.dispute_log or [],
        "compliance_status": memory.compliance_status or {},
        "relationship_health_score": memory.relationship_health_score,
        "source_documents": memory.source_documents or [],
        "last_updated": memory.last_updated.isoformat() if memory.last_updated else None,
    }


def list_suppliers(user_id: str, status: str | None = "active") -> list[dict]:
    with SessionLocal() as session:
        query = session.query(Supplier).filter(Supplier.user_id == uuid.UUID(user_id))
        if status:
            query = query.filter(Supplier.status == status)
        return [_serialize_supplier(s) for s in query.order_by(Supplier.name).all()]


def get_or_create_supplier(user_id: str, name: str, **kwargs) -> dict:
    with SessionLocal() as session:
        supplier = (
            session.query(Supplier)
            .filter(Supplier.user_id == uuid.UUID(user_id), Supplier.name.ilike(name))
            .first()
        )
        if not supplier:
            supplier = Supplier(
                user_id=uuid.UUID(user_id),
                name=name,
                status=kwargs.get("status", "active"),
                contact_email=kwargs.get("contact_email"),
                category=kwargs.get("category"),
                metadata_json=kwargs.get("metadata", {}),
            )
            session.add(supplier)
            session.commit()
            session.refresh(supplier)
        return _serialize_supplier(supplier)


def _extract_payment_signals(text: str) -> list[dict]:
    payments = []
    net_terms = re.findall(r"net[- ]?(\d+)", text, re.IGNORECASE)
    if net_terms:
        payments.append({"type": "payment_terms", "value": f"Net-{net_terms[0]}", "source": "document"})
    currency_amounts = re.findall(r"(CFA|USD|EUR|GBP)\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    for currency, amount in currency_amounts[:5]:
        payments.append({"type": "amount_reference", "value": f"{currency} {amount}", "source": "document"})
    return payments


def _extract_disputes(text: str) -> list[dict]:
    dispute_keywords = ["dispute", "claim", "breach", "penalty", "non-conformance", "quality issue"]
    disputes = []
    for line in text.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in dispute_keywords):
            disputes.append({"description": line.strip()[:300], "source": "document"})
    return disputes[:5]


def _extract_compliance(text: str) -> dict:
    compliance = {"certifications": [], "audit_status": "unknown", "flags": []}
    cert_patterns = ["ISO 9001", "ISO 14001", "SOC 2", "GDPR", "REACH", "RoHS"]
    for cert in cert_patterns:
        if cert.lower() in text.lower():
            compliance["certifications"].append(cert)
    if "non-compliant" in text.lower() or "violation" in text.lower():
        compliance["flags"].append("Compliance concern detected in documents")
        compliance["audit_status"] = "review_required"
    elif compliance["certifications"]:
        compliance["audit_status"] = "compliant"
    return compliance


def _compute_health_score(
    payment_history: list,
    dispute_log: list,
    compliance_status: dict,
    doc_count: int,
) -> float:
    score = 70.0
    if doc_count >= 2:
        score += 10
    if payment_history:
        score += 5
    score -= min(len(dispute_log) * 8, 30)
    if compliance_status.get("audit_status") == "compliant":
        score += 10
    elif compliance_status.get("audit_status") == "review_required":
        score -= 15
    if compliance_status.get("flags"):
        score -= 5 * len(compliance_status["flags"])
    return max(0.0, min(100.0, round(score, 1)))


def compile_deal_memory(
    user_id: str,
    supplier_name: str,
    collection=None,
    chat_id: str | None = None,
) -> dict:
    """Compile or refresh a deal memory dossier for an active supplier."""
    supplier_data = get_or_create_supplier(user_id, supplier_name)

    source_documents: list[str] = []
    combined_text = ""
    contract_summary = ""

    if collection is not None:
        queries = [
            f"{supplier_name} contract agreement terms",
            f"{supplier_name} payment invoice",
            f"{supplier_name} amendment dispute compliance",
        ]
        seen_docs: set[str] = set()
        for query in queries:
            matches = query_scope_matches(
                collection,
                query,
                user_id=user_id,
                chat_id=chat_id,
                n_results=4,
                include_user_knowledge=True,
            )
            for doc, meta in matches:
                meta = meta or {}
                filename = str(meta.get("filename") or "Unknown")
                if filename not in seen_docs:
                    seen_docs.add(filename)
                    source_documents.append(filename)
                combined_text += f"\n{doc}"

        if combined_text.strip():
            summary_lines = [
                line.strip()
                for line in combined_text.splitlines()
                if line.strip() and len(line.strip()) > 20
            ]
            contract_summary = " ".join(summary_lines[:8])[:2000]
            if len(contract_summary) > 500:
                contract_summary = contract_summary[:500] + "..."

    payment_history = _extract_payment_signals(combined_text)
    dispute_log = _extract_disputes(combined_text)
    compliance_status = _extract_compliance(combined_text)
    health_score = _compute_health_score(
        payment_history, dispute_log, compliance_status, len(source_documents)
    )

    with SessionLocal() as session:
        supplier = session.get(Supplier, uuid.UUID(supplier_data["id"]))
        memory = (
            session.query(DealMemory)
            .filter(DealMemory.supplier_id == supplier.id)
            .first()
        )
        if memory:
            memory.contract_summary = contract_summary or memory.contract_summary
            memory.payment_history = payment_history or memory.payment_history
            memory.dispute_log = dispute_log or memory.dispute_log
            memory.compliance_status = compliance_status
            memory.relationship_health_score = health_score
            memory.source_documents = source_documents
        else:
            memory = DealMemory(
                supplier_id=supplier.id,
                user_id=uuid.UUID(user_id),
                contract_summary=contract_summary,
                payment_history=payment_history,
                dispute_log=dispute_log,
                compliance_status=compliance_status,
                relationship_health_score=health_score,
                source_documents=source_documents,
            )
            session.add(memory)
        session.commit()
        session.refresh(memory)
        return _serialize_deal_memory(memory, supplier.name)


def get_deal_memory(user_id: str, supplier_name: str) -> dict | None:
    with SessionLocal() as session:
        supplier = (
            session.query(Supplier)
            .filter(Supplier.user_id == uuid.UUID(user_id), Supplier.name.ilike(supplier_name))
            .first()
        )
        if not supplier:
            return None
        memory = (
            session.query(DealMemory)
            .filter(DealMemory.supplier_id == supplier.id)
            .first()
        )
        if not memory:
            return None
        return _serialize_deal_memory(memory, supplier.name)
