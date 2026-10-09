from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.shortcuts import redirect, render

from billing.models import Plan
from config.decorators import allowed_users
from config.forms import BootstrapModelForm
from config.models import SystemSetting
from config.user_utils import user_group


class SettingForm(BootstrapModelForm):
	class Meta:
		model = SystemSetting
		fields = ['tutor_prompt_extra', 'payments_required', 'free_turns_per_day', 'paid_turns_per_day']
		widgets = {'tutor_prompt_extra': forms.Textarea(attrs={'rows': 6})}

	def clean_tutor_prompt_extra(self):
		return self.cleaned_data['tutor_prompt_extra'].strip()


class PlanForm(BootstrapModelForm):
	class Meta:
		model = Plan
		fields = ['label', 'price_usd', 'hours', 'active']

	def clean_price_usd(self):
		price = self.cleaned_data['price_usd']
		if price < 0 or price > 10000:
			raise forms.ValidationError('Folin tenke entre 0 no 10000.')
		return price

	def clean_hours(self):
		hours = self.cleaned_data['hours']
		if not 1 <= hours <= 24 * 366 * 5:
			raise forms.ValidationError('Oras tenke entre 1 no 43920 (tinan 5).')
		return hours


PlanFormSet = modelformset_factory(Plan, form=PlanForm, extra=0)


@login_required
@allowed_users(allowed_roles=['admin'])
def SystemSettings(request):
	setting = SystemSetting.load()
	plans = Plan.objects.order_by('sort')
	if request.method == 'POST':
		form = SettingForm(request.POST, instance=setting)
		formset = PlanFormSet(request.POST, queryset=plans, prefix='plan')
		if form.is_valid() and formset.is_valid():
			form.save()
			formset.save()
			messages.success(request, 'Konfigurasaun rai ona.')
			return redirect('system_settings')
	else:
		form = SettingForm(instance=setting)
		formset = PlanFormSet(queryset=plans, prefix='plan')
	context = {
        'group': user_group(request.user), 'page': 'config', 'form': form, 'formset': formset,
        'title': 'Konfigurasaun sistema', 'legend': 'Konfigurasaun sistema',
    }
	return render(request, 'config/settings.html', context)
