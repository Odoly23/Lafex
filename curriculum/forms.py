from django import forms

from config.forms import BootstrapModelForm

from .models import Mission


class MissionForm(BootstrapModelForm):
	rubric_text = forms.CharField(
        label='Rubrika avaliasaun (Inglés, liña ida = pontu ida)', required=False,
        widget=forms.Textarea(attrs={'rows': 4}))

	class Meta:
		model = Mission
		fields = ['title_tet', 'title_en', 'goal_tet', 'goal_en', 'ai_role', 'max_turns', 'active']
		widgets = {k: forms.Textarea(attrs={'rows': 3}) for k in ('goal_tet', 'goal_en', 'ai_role')}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['rubric_text'].initial = '\n'.join(self.instance.rubric or [])
		self._bootstrapify()

	def clean_max_turns(self):
		n = self.cleaned_data['max_turns']
		if not 1 <= n <= 60:
			raise forms.ValidationError('Dalan maksimu tenke entre 1 no 60.')
		return n

	def save(self, commit=True):
		obj = super().save(commit=False)
		lines = [l.strip()[:200] for l in self.cleaned_data['rubric_text'].splitlines() if l.strip()]
		obj.rubric = lines[:10]
		if commit:
			obj.save()
		return obj
