from django.urls import path

from . import staff_views as v

urlpatterns = [
    path('', v.VoucherList, name='voucher_list'),
    path('batch/<int:pk>/', v.VoucherBatchDetail, name='voucher_batch'),
    path('batch/<int:pk>/cetak/', v.VoucherPrint, name='voucher_print'),
    path('batch/<int:pk>/kansela/', v.VoucherBatchVoid, name='voucher_batch_void'),
    path('<int:pk>/kansela/', v.VoucherVoid, name='voucher_void'),
]
