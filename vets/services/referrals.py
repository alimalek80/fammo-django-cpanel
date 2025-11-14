from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from django.contrib.sites.models import Site
from django.conf import settings

from ..models import ReferralCode, ReferredUser, Clinic, ReferralStatus


@dataclass
class AttachResult:
    ok: bool
    reason: Optional[str] = None


def build_referral_signup_url(code: str) -> str:
    """
    Build a full URL like https://domain/signup/?ref=<code>.
    If you already have SITE_URL, use that instead of Sites framework.
    """
    base = getattr(settings, "SITE_URL", None)
    if not base:
        current = Site.objects.get_current()
        base = f"https://{current.domain}"
    return f"{base}/signup/?ref={code}"


def attach_referral_to_user(user, ref_code: str) -> AttachResult:
    """
    Resolve a referral code and attach the user to the clinic, creating ReferredUser.
    Idempotent per (clinic, user).
    """
    try:
        code = ReferralCode.objects.get(code=ref_code, is_active=True)
    except ReferralCode.DoesNotExist:
        return AttachResult(False, "invalid_or_inactive_code")

    clinic: Clinic = code.clinic
    obj, created = ReferredUser.objects.get_or_create(
        clinic=clinic,
        user=user,
        defaults={"referral_code": code, "status": ReferralStatus.ACTIVE},
    )
    if not created:
        # update if previously NEW/INACTIVE
        if obj.status != ReferralStatus.ACTIVE:
            obj.status = ReferralStatus.ACTIVE
            obj.referral_code = obj.referral_code or code
            obj.save(update_fields=["status", "referral_code", "updated_at"])
    return AttachResult(True)
