from collections import Counter
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework.response import Response

from billing.models import Entitlement, Voucher
from config.api import APIStaff
from curriculum.models import Mission
from tutor.models import Session
from users.models import LEVELS, User


class APIStats(APIStaff):
	def get(self, request, format=None):
		now = timezone.now()
		data = {
            'siswa': User.objects.filter(groups__name='estudante').count(),
            'sesaun': Session.objects.filter(finished_at__isnull=False).count(),
            'pakote_ativu': Entitlement.objects.filter(expires_at__gt=now).count(),
            'vaucher_livre': Voucher.objects.filter(used_by__isnull=True).count(),
        }
		return Response(data)


class APISesaunDaily(APIStaff):
	"""Sesi selesai per hari, 14 hari terakhir (hari tanpa sesi tetap muncul dengan 0).
	Dihitung di Python: fungsi tanggal berzona waktu di MySQL butuh tabel zona waktu yang sering belum dimuat."""
	def get(self, request, format=None):
		today = timezone.localdate()
		days = [today - timedelta(days=i) for i in range(13, -1, -1)]
		start = timezone.make_aware(datetime.combine(days[0], time.min))
		finished = Session.objects.filter(finished_at__gte=start).values_list('finished_at', flat=True)
		by_day = Counter(timezone.localtime(t).date() for t in finished)
		return Response({'label': [d.strftime('%d/%m') for d in days], 'obj': [by_day.get(d, 0) for d in days]})


class APILevels(APIStaff):
	def get(self, request, format=None):
		rows = dict(User.objects.filter(groups__name='estudante').values_list('level').annotate(n=Count('id')))
		return Response({'label': LEVELS, 'obj': [rows.get(l, 0) for l in LEVELS]})


class APIMisaun(APIStaff):
	"""Jumlah sesi selesai dan rata-rata nilai per misi."""
	def get(self, request, format=None):
		rows = {r['mission_id']: r for r in
                Session.objects.filter(finished_at__isnull=False, mission__is_placement=False)
                .values('mission_id').annotate(n=Count('id'), avg=Avg('score'))}
		label, obj, avg = [], [], []
		for m in Mission.objects.filter(is_placement=False, active=True):
			r = rows.get(m.id)
			label.append(m.title_tet)
			obj.append(r['n'] if r else 0)
			avg.append(round(r['avg']) if r else 0)
		return Response({'label': label, 'obj': obj, 'avg': avg})


class APIVaucher(APIStaff):
	def get(self, request, format=None):
		used = Voucher.objects.filter(used_by__isnull=False).count()
		free = Voucher.objects.filter(used_by__isnull=True).count()
		return Response({'label': ['Uza tiha', 'Seidauk uza'], 'obj': [used, free]})
