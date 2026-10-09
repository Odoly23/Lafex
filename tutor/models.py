from django.conf import settings
from django.db import models
from django.utils import timezone


class Session(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    mission = models.ForeignKey('curriculum.Mission', on_delete=models.PROTECT)
    level_start = models.CharField(max_length=2)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    level_end = models.CharField(max_length=2, blank=True)
    summary = models.JSONField(default=dict, blank=True)   # headline, tips, vocab, corrections (Tetun)

    class Meta:
        ordering = ['-started_at']
        indexes = [models.Index(fields=['user', 'finished_at'])]


class Turn(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='turns')
    idx = models.PositiveSmallIntegerField()
    role = models.CharField(max_length=9, choices=[('user', 'user'), ('assistant', 'assistant')])
    text = models.TextField()
    correction = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['idx']
        unique_together = [('session', 'idx')]
