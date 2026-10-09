from django import forms

from config.forms import BootstrapForm, BootstrapModelForm
from curriculum.models import BANDS

from .models import QuizQuestion


class QuestionForm(BootstrapModelForm):
	class Meta:
		model = QuizQuestion
		fields = ['question', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'answer', 'explanation_tet', 'band', 'active']


class ImportForm(BootstrapForm):
	band = forms.ChoiceField(choices=BANDS, label='Band nível ba pergunta ne\'e')
	lines = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label='Lista pergunta')
