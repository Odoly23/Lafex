from django.urls import path

from . import staff_views as v

urlpatterns = [
    path('', v.QuestionList, name='quiz_questions'),
    path('novu/', v.QuestionEdit, name='quiz_question_new'),
    path('import/', v.QuestionImport, name='quiz_import'),
    path('<int:pk>/edita/', v.QuestionEdit, name='quiz_question_edit'),
    path('<int:pk>/hamoos/', v.QuestionDelete, name='quiz_question_delete'),
]
