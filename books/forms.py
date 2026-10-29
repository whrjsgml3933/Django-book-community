from django import forms
from django.conf import settings
from .models import Book


class BookForm(forms.ModelForm):
    generate_author = forms.BooleanField(
        label='작가 정보와 대표작도 함께 생성', required=False,
        help_text='선택하면 작가 이름으로 위키백과를 검색하고, 작가 이름·도서 제목·검색 정보를 GMS에 보내 소개를 만듭니다. 생성에는 잠시 시간이 걸릴 수 있습니다.',
    )

    class Meta:
        model = Book
        fields = ['title', 'content', 'star_avg', 'author']
        labels = {'title': '도서 제목', 'content': '도서 설명', 'star_avg': '평점', 'author': '저자'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['generate_author'].initial = bool(settings.GMS_API_KEY) and not self.instance.pk
        if not settings.GMS_API_KEY:
            self.fields['generate_author'].help_text = 'GMS API 키를 설정한 뒤 작가 정보를 생성할 수 있습니다. 도서만 등록하는 것도 가능합니다.'
