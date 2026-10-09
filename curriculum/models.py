from django.db import models

BANDS = [('beginner', 'Pemula (A1-A2)'), ('intermediate', 'Menengah (B1-B2)'), ('advanced', 'Lanjut (C1-C2)')]
BAND_LEVELS = {'beginner': ('A1', 'A2'), 'intermediate': ('B1', 'B2'), 'advanced': ('C1', 'C2')}


def band_for_level(level):
    for band, levels in BAND_LEVELS.items():
        if level in levels:
            return band
    return 'beginner'


class Scenario(models.Model):
    slug = models.SlugField(unique=True)
    title_tet = models.CharField(max_length=80)
    title_en = models.CharField(max_length=80)
    emoji = models.CharField(max_length=8, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title_en


class Mission(models.Model):
    """Satu role-play: AI memerankan `ai_role`, siswa harus mencapai `goal_en`."""
    scenario = models.ForeignKey(Scenario, null=True, blank=True, on_delete=models.CASCADE, related_name='missions')
    slug = models.SlugField(unique=True)
    band = models.CharField(max_length=12, choices=BANDS)
    order = models.PositiveSmallIntegerField(default=0)
    title_tet = models.CharField(max_length=100)
    title_en = models.CharField(max_length=100)
    goal_tet = models.TextField()                 # ditampilkan ke siswa (Tetun)
    goal_en = models.TextField()                  # dipakai AI untuk menilai tercapai/tidak
    ai_role = models.TextField()                  # peran dan situasi untuk AI (Inggris)
    rubric = models.JSONField(default=list)       # poin penilaian (Inggris)
    max_turns = models.PositiveSmallIntegerField(default=12)
    is_placement = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['scenario__order', 'band', 'order']

    def __str__(self):
        return f'{self.slug} [{self.band}]'
