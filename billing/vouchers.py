"""Kode voucher gaya pulsa/token: acak, sekali pakai, dan hanya disimpan sebagai hash.

- Alfabet 32 karakter tanpa huruf yang mudah tertukar (I, L, O, U): kode mudah dibaca dan diketik dari kartu cetak.
- 12 karakter = 60 bit acak, tidak bisa ditebak; ditambah pembatasan percobaan salah (lihat services.redeem).
- Database hanya menyimpan HMAC-SHA256(kode, pepper), jadi kebocoran database tidak membocorkan kode yang belum dipakai.
"""
import hashlib
import hmac
import secrets

from django.conf import settings

ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
CODE_LENGTH = 12
_FIX = str.maketrans({'O': '0', 'I': '1', 'L': '1'})  # salah ketik yang umum


def generate_code():
	raw = ''.join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
	return '-'.join(raw[i:i + 4] for i in range(0, CODE_LENGTH, 4))


def normalize(code):
	return ''.join(ch for ch in str(code or '').upper() if ch.isalnum()).translate(_FIX)


def pepper():
	return getattr(settings, 'VOUCHER_PEPPER', None) or settings.SECRET_KEY


def hash_code(code):
	return hmac.new(pepper().encode(), normalize(code).encode(), hashlib.sha256).hexdigest()


def looks_valid(code):
	n = normalize(code)
	return len(n) == CODE_LENGTH and all(c in ALPHABET for c in n)
