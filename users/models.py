from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, PermissionsMixin
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
		role = 'admin' if user.is_superuser else 'staff' if user.is_staff else 'estudante'
		user.groups.add(Group.objects.get_or_create(name=role)[0])  # peran lewat Django Groups
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
	email = models.EmailField(unique=True, verbose_name='Email')
	name = models.CharField(max_length=80, blank=True, verbose_name='Naran')
	level = models.CharField(max_length=2, default='A1', choices=[(l, l) for l in LEVELS], verbose_name='Nível')
	placement_done = models.BooleanField(default=False, verbose_name='Teste nível kompletu')
	is_active = models.BooleanField(default=True, verbose_name='Ativu')
	is_staff = models.BooleanField(default=False, verbose_name='Bele tama admin')
	date_joined = models.DateTimeField(default=timezone.now, verbose_name='Data tama')
	points = models.PositiveIntegerField(default=0, verbose_name='Pontu')
	streak = models.PositiveIntegerField(default=0, verbose_name='Streak (loron-loron)')
	best_streak = models.PositiveIntegerField(default=0, verbose_name='Streak di\'ak liu')
	last_active = models.DateField(null=True, blank=True, verbose_name='Loron ativu ikus')

	objects = UserManager()

	class Meta:
		verbose_name = 'Utilizadór'
		verbose_name_plural = 'Utilizadór'

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
