from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        email = self.normalize(email)
        if not email:
            raise ValueError('email wajib diisi')
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # pengguna biasa masuk lewat kode email
        user.save(using=self._db)
        return user

    @staticmethod
    def normalize(email):
        return (email or '').strip().lower()

    def create_user(self, email, password=None, **extra):
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=80, blank=True)
    level = models.CharField(max_length=2, default='A1', choices=[(l, l) for l in LEVELS])
    placement_done = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class LoginCode(models.Model):
    """Kode 6 digit sekali pakai. Yang disimpan hanya hash-nya."""
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
