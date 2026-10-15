import os

from receipt_service import (
    InfraiClient,
    InspectionReminder,
    MaintenanceRequest,
    PropertyOrder,
    TenantDocument,
    send_property_receipt,
)


def main() -> None:
    recipient = os.environ.get("DEMO_EMAIL_TO")
    if not recipient:
        raise SystemExit("DEMO_EMAIL_TO is required")
    order = PropertyOrder(
        tenant_email=recipient,
        property_name="Maple Court",
        requests=(MaintenanceRequest("Leaking tap", "urgent"),),
        documents=(TenantDocument("Lease", "verified"), TenantDocument("Pet addendum", "pending")),
        inspection=InspectionReminder("2026-10-03", "Bring access code"),
    )
    result = send_property_receipt(InfraiClient(), order)
    print("receipt sent; message status:", result["status"]["data"])


if __name__ == "__main__":
    main()
