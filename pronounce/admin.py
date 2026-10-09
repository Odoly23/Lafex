from django.contrib import admin

from .models import PronAttempt, PronPhrase

admin.site.register(PronPhrase)
admin.site.register(PronAttempt)
