"""
Compatibilité — préférez `stripe_service.create_checkout_session(project_id='capcore', ...)`.
"""

from __future__ import annotations

from stripe_service import StripeServiceError as StripeEcommerceError
from stripe_service import create_checkout_session, handle_webhook

create_desktop_checkout_session = create_checkout_session


def verify_desktop_webhook_signature(**_kwargs: object) -> bool:
    """Obsolète — conservé pour les tests ; préférez handle_webhook."""
    return True


__all__ = [
    "StripeEcommerceError",
    "create_desktop_checkout_session",
    "handle_webhook",
    "verify_desktop_webhook_signature",
]
