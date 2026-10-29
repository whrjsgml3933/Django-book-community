from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


GENRE_CHOICES = [
    ('소설', '소설'), ('시·에세이', '시·에세이'), ('인문', '인문'),
    ('사회', '사회'), ('과학', '과학'), ('경제·경영', '경제·경영'),
    ('자기계발', '자기계발'), ('예술', '예술'),
]


class User(AbstractUser):
    gender = models.CharField('성별', max_length=10, blank=True, choices=[
        ('female', '여성'), ('male', '남성'), ('other', '기타'), ('private', '응답 안 함'),
    ])
    age = models.PositiveIntegerField('나이', null=True, blank=True, validators=[MinValueValidator(1)])
    weekly_reading_hours = models.PositiveIntegerField('주간 평균 독서 시간', null=True, blank=True, validators=[MinValueValidator(1)], help_text='일주일 동안 책을 읽는 시간입니다. 입력할 경우 1시간 이상으로 적어 주세요.')
    annual_reading_count = models.PositiveIntegerField('연간 독서량', null=True, blank=True, validators=[MinValueValidator(1)], help_text='한 해에 읽는 책의 수입니다. 입력할 경우 1권 이상으로 적어 주세요.')
    interested_genres = models.CharField('관심 장르', max_length=600, blank=True)

    @property
    def genre_list(self):
        # ModelForm 검증 중에는 선택값이 일시적으로 리스트일 수 있습니다.
        if isinstance(self.interested_genres, list):
            return self.interested_genres
        return [genre for genre in self.interested_genres.split(',') if genre]
