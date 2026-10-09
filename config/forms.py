from django import forms


class BootstrapMixin:
	"""Beri class Bootstrap 4 pada semua widget supaya form tampil seragam."""

	def _bootstrapify(self):
		for field in self.fields.values():
			w = field.widget
			if isinstance(w, forms.CheckboxInput):
				w.attrs['class'] = 'form-check-input'
			elif isinstance(w, forms.Select):
				w.attrs['class'] = 'custom-select'
			elif not isinstance(w, forms.HiddenInput):
				w.attrs['class'] = 'form-control'


class BootstrapModelForm(BootstrapMixin, forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._bootstrapify()


class BootstrapForm(BootstrapMixin, forms.Form):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._bootstrapify()
