from django.urls import path

from . import staff_views as v

urlpatterns = [
    path('', v.CategoryList, name='vocab_categories'),
    path('kategoria/novu/', v.CategoryEdit, name='vocab_category_new'),
    path('kategoria/<int:pk>/edita/', v.CategoryEdit, name='vocab_category_edit'),
    path('<int:pk>/', v.ItemList, name='vocab_items'),
    path('<int:pk>/import/', v.ItemImport, name='vocab_import'),
    path('<int:category_pk>/item/novu/', v.ItemEdit, name='vocab_item_new'),
    path('item/<int:pk>/edita/', v.ItemEdit, name='vocab_item_edit'),
    path('item/<int:pk>/hamoos/', v.ItemDelete, name='vocab_item_delete'),
]
