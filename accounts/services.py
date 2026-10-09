import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import LoginCode

User = get_user_model()


class RateLimited(Exception):
    pass


def clean_email(raw):
    if not isinstance(raw, str):
        return None
    email = User.objects.normalize(raw)
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email if len(email) <= 254 else None


def _hash(email, code):
    # HMAC dengan SECRET_KEY: kode 6 digit tidak bisa ditebak dari basis data yang bocor.
    return hmac.new(settings.SECRET_KEY.encode(), f'{email}:{code}'.encode(), hashlib.sha256).hexdigest()


def issue_code(email):
    now = timezone.now()
    recent = LoginCode.objects.filter(email=email, created_at__gte=now - timedelta(hours=1)).count()
    if recent >= settings.LOGIN_CODES_PER_HOUR:
        raise RateLimited()
    code = f'{secrets.randbelow(10**6):06d}'
    LoginCode.objects.create(
        email=email, code_hash=_hash(email, code),
        expires_at=now + timedelta(minutes=settings.LOGIN_CODE_TTL_MINUTES),
    )
    minutes = settings.LOGIN_CODE_TTL_MINUTES
    send_mail(
        subject=f'Lafex: kódigu {code}',
        message=(
            f"Kódigu Lafex ita nian: {code}\n"
            f"Válidu ba minutu {minutes}. Se la'ós ita mak husu, haluha de'it email ida-ne'e.\n\n"
            f"Kode masuk Lafex Anda: {code}\n"
            f"Berlaku {minutes} menit. Jika bukan Anda yang meminta, abaikan email ini."
        ),
        from_email=None, recipient_list=[email],
    )


@transaction.atomic
def verify_code(email, code):
    """Kembalikan (user, dibuat_baru) bila kode benar, selain itu None."""
    now = timezone.now()
    row = (LoginCode.objects.select_for_update()
           .filter(email=email, used_at__isnull=True, expires_at__gt=now)
           .order_by('-created_at').first())
    if not row or row.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS:
        return None
    row.attempts += 1
    ok = hmac.compare_digest(row.code_hash, _hash(email, str(code).strip()))
    if ok:
        row.used_at = now
    row.save(update_fields=['attempts', 'used_at'])
    if not ok:
        return None
    user, created = User.objects.get_or_create(email=email)
    if not user.is_active:
        return None
    return user, created
