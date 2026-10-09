from config.forms import BootstrapModelForm

from .models import VocabCategory, VocabItem


class CategoryForm(BootstrapModelForm):
	class Meta:
		model = VocabCategory
		fields = ['slug', 'name_tet', 'name_en', 'emoji', 'order', 'active']


class ItemForm(BootstrapModelForm):
	class Meta:
		model = VocabItem
		fields = ['tet', 'en', 'example_en', 'order', 'active']
