from receipt_service import (
    InfraiClient,
    InspectionReminder,
    MaintenanceRequest,
    PropertyOrder,
    TenantDocument,
    build_receipt,
)


def test_receipt_counts_urgent_requests_and_lists_property_context():
    order = PropertyOrder(
        tenant_email="tenant@example.com",
        property_name="Maple Court",
        requests=(MaintenanceRequest("Leaking tap", "urgent"), MaintenanceRequest("Paint hallway", "normal")),
        documents=(TenantDocument("Lease", "verified"),),
        inspection=InspectionReminder("2026-10-03", "Bring access code"),
    )
    subject, html = build_receipt(order)
    assert subject == "Maple Court service receipt"
    assert "Maintenance requests: 2 (urgent: 1)" in html
    assert "Lease (verified)" in html
    assert "2026-10-03" in html


def test_client_requires_environment_key(monkeypatch):
    monkeypatch.delenv("INFRAI_API_KEY", raising=False)
    try:
        InfraiClient()
    except ValueError as exc:
        assert "INFRAI_API_KEY" in str(exc)
    else:
        raise AssertionError("missing key should be rejected")
