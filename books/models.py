from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    star_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    author = models.CharField(max_length=100)
    author_info = models.TextField('작가 정보', blank=True)
    author_works = models.JSONField('작가 대표작', default=list, blank=True)
    author_photo = models.URLField('작가 사진', max_length=1000, blank=True)
    author_source = models.URLField('작가 정보 출처', max_length=1000, blank=True)
    author_generated_at = models.DateTimeField('작가 정보 생성 일시', null=True, blank=True)

    def __str__(self):
        return self.title
