from django.urls import path

from . import staff_views

urlpatterns = [
    path('', staff_views.StudentList, name='student_list'),
    path('<int:pk>/', staff_views.StudentEdit, name='student_edit'),
]
