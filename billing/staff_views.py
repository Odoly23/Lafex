from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from config.decorators import allowed_users
from config.user_utils import user_group

from . import services
from .models import Plan, Voucher

MAX_BATCH = 200


@login_required
@allowed_users(allowed_roles=['admin'])
def VoucherList(request):
	if request.method == 'POST':
		plan = Plan.objects.filter(code=request.POST.get('plan'), active=True).first()
		try:
			count = int(request.POST.get('count', ''))
		except ValueError:
			count = 0
		if not plan or not 1 <= count <= MAX_BATCH:
			messages.error(request, f'Pakote ka kuantidade la loos (1-{MAX_BATCH}).')
		else:
			# Kode baru disimpan sementara di sesi admin dan ditampilkan sekali (pola PRG).
			request.session['new_codes'] = services.create_vouchers(plan.code, count)
			messages.success(request, f'Vaucher {count} ({plan.label}) kria ona.')
		return redirect('voucher_list')
	context = {
        'group': user_group(request.user), 'page': 'vaucher',
        'new_codes': request.session.pop('new_codes', []),
        'plans': Plan.objects.filter(active=True),
        'objects': Voucher.objects.select_related('plan', 'used_by').order_by('-created_at')[:1000],
        'title': 'Lista Vaucher', 'legend': 'Lista Vaucher',
    }
	return render(request, 'billing/list.html', context)
