import segno
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.decorators import allowed_users
from config.user_utils import user_group

from . import services
from .models import Plan, Voucher, VoucherBatch

ROLES = ['admin']
MAX_BATCH = 500
MAX_VALID_DAYS = 1095


def _ctx(request, **extra):
	return {'group': user_group(request.user), 'page': 'vaucher', **extra}


@login_required
@allowed_users(allowed_roles=ROLES)
def VoucherList(request):
	if request.method == 'POST':
		plan = Plan.objects.filter(code=request.POST.get('plan'), active=True).first()
		label = ' '.join(request.POST.get('label', '').split())[:80]
		try:
			count, days = int(request.POST.get('count', '')), int(request.POST.get('valid_days', '365'))
		except ValueError:
			count = days = 0
		if not plan or not label or not 1 <= count <= MAX_BATCH or not 1 <= days <= MAX_VALID_DAYS:
			messages.error(request, f'Pakote, naran toko, kuantidade (1-{MAX_BATCH}) ka loron válidu (1-{MAX_VALID_DAYS}) la loos.')
			return redirect('voucher_list')
		batch, rows = services.create_batch(plan, count, label, created_by=request.user, valid_days=days)
		# Kode rahasia hanya ada sekarang. Disimpan sementara di sesi admin dan hanya ditampilkan SEKALI di halaman cetak.
		request.session['print_batch'] = {'batch': batch.pk, 'rows': rows}
		return redirect('voucher_print', pk=batch.pk)
	batches = (VoucherBatch.objects.select_related('plan')
               .annotate(n_used=Count('vouchers', filter=Q(vouchers__used_by__isnull=False)),
                         n_void=Count('vouchers', filter=Q(vouchers__voided_at__isnull=False, vouchers__used_by__isnull=True)))
               .order_by('-created_at', '-pk')[:500])  # eksplisit: Meta.ordering diabaikan pada query annotate
	stats = [{'b': b, 'revenue': b.n_used * b.plan.price_usd, 'left': b.quantity - b.n_used - b.n_void} for b in batches]
	return render(request, 'billing/list.html', _ctx(
        request, stats=stats, plans=Plan.objects.filter(active=True), title='Vaucher', legend='Batch vaucher'))


@login_required
@allowed_users(allowed_roles=ROLES)
def VoucherPrint(request, pk):
	"""Halaman cetak kartu (sekali tampil). Setelah ini kode tidak bisa dilihat lagi, hanya nomor seri."""
	batch = get_object_or_404(VoucherBatch.objects.select_related('plan'), pk=pk)
	stash = request.session.pop('print_batch', None)
	cards = None
	if stash and stash.get('batch') == batch.pk:
		base = request.build_absolute_uri('/')
		cards = [{
            'serial': serial, 'code': code,
            'qr': segno.make(f'{base}?kode={code}', error='m').svg_inline(scale=3, omitsize=True, dark='#2e3131', border=1),
        } for serial, code in stash['rows']]
	meta = {'batch': batch.pk, 'plan': batch.plan.label, 'valid_until': batch.valid_until.date().isoformat(), 'shop': batch.label}
	return render(request, 'billing/print.html', {'batch': batch, 'cards': cards, 'meta': meta, 'title': f'Cetak batch #{batch.pk}'})


@login_required
@allowed_users(allowed_roles=ROLES)
def VoucherBatchDetail(request, pk):
	batch = get_object_or_404(VoucherBatch.objects.select_related('plan'), pk=pk)
	objects = batch.vouchers.select_related('used_by', 'batch').order_by('serial')
	return render(request, 'billing/batch.html', _ctx(
        request, batch=batch, objects=objects, title=f'Batch #{batch.pk}', legend=f'Batch #{batch.pk}: {batch.label}'))


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def VoucherBatchVoid(request, pk):
	batch = get_object_or_404(VoucherBatch, pk=pk)
	services.void_batch(batch)
	messages.success(request, 'Batch kansela ona: vaucher ne\'ebé seidauk uza la válidu tan.')
	return redirect('voucher_batch', pk=batch.pk)


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def VoucherVoid(request, pk):
	voucher = get_object_or_404(Voucher, pk=pk)
	if services.void_voucher(voucher):
		messages.success(request, f'Vaucher {voucher.serial} kansela ona.')
	else:
		messages.warning(request, f'Vaucher {voucher.serial} la bele kansela (uza ona ka kansela ona).')
	return redirect('voucher_batch', pk=voucher.batch_id) if voucher.batch_id else redirect('voucher_list')
