from django import forms

from billing.models import Plan
from config.forms import BootstrapModelForm

from .models import User


class StudentForm(BootstrapModelForm):
	grant_plan = forms.ModelChoiceField(
        queryset=Plan.objects.filter(active=True), required=False, empty_label='(la fó pakote)',
        label='Fó pakote (manual)', help_text='Aumenta masa ativu ba estudante (ba admin de\'it).')

	class Meta:
		model = User
		fields = ['name', 'level', 'is_active']

	def __init__(self, *args, can_grant=False, **kwargs):
		super().__init__(*args, **kwargs)
		if not can_grant:
			del self.fields['grant_plan']
