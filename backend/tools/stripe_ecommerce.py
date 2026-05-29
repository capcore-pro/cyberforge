"""
Compatibilité — préférez `stripe_service` pour les nouveaux appels Stripe.
"""

from __future__ import annotations

from stripe_service import StripeServiceError as StripeEcommerceError
from stripe_service import create_checkout_session, handle_webhook

__all__ = [
    "StripeEcommerceError",
    "create_checkout_session",
    "handle_webhook",
]
