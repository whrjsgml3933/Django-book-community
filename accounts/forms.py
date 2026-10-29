from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import GENRE_CHOICES


PROFILE_FIELDS = (
    'username', 'email', 'last_name', 'first_name', 'gender', 'age',
    'weekly_reading_hours', 'annual_reading_count', 'interested_genres',
)
LABELS = {'username': '아이디', 'email': '이메일', 'last_name': '성', 'first_name': '이름'}


class CustomUserCreationForm(UserCreationForm):
    interested_genres = forms.MultipleChoiceField(
        label='관심 장르', choices=GENRE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}), required=False,
        help_text='좋아하는 장르를 여러 개 선택할 수 있습니다.',
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = PROFILE_FIELDS
        labels = LABELS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = '비밀번호'
        self.fields['password2'].label = '비밀번호 확인'


class CustomUserChangeForm(UserChangeForm):
    password = None
    interested_genres = forms.MultipleChoiceField(
        label='관심 장르', choices=GENRE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}), required=False,
    )

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = PROFILE_FIELDS
        labels = LABELS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['interested_genres'] = self.instance.genre_list


# 기존 코드에서 사용하던 이름도 유지합니다.
UserCreation = CustomUserCreationForm
UserChange = CustomUserChangeForm
