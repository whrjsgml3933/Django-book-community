from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, Client
from django.urls import reverse

from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()
PASSWORD = 'Reader!Thread_418'


class ReadingProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reader', password=PASSWORD, email='reader@example.com')

    def test_user_extension_and_form_types(self):
        self.assertIsInstance(User._meta.get_field('interested_genres'), models.CharField)
        self.assertEqual(User._meta.get_field('interested_genres').max_length, 600)
        self.assertTrue(issubclass(CustomUserCreationForm, UserCreationForm))
        self.assertTrue(issubclass(CustomUserChangeForm, UserChangeForm))
        field = CustomUserCreationForm().fields['interested_genres']
        self.assertIsInstance(field, forms.MultipleChoiceField)
        self.assertIsInstance(field.widget, forms.CheckboxSelectMultiple)

    def test_signup_saves_genres_and_logs_in(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newreader', 'email': 'new@example.com', 'last_name': '김', 'first_name': '독자',
            'password1': PASSWORD, 'password2': PASSWORD, 'gender': 'female', 'age': 24,
            'weekly_reading_hours': 5, 'annual_reading_count': 18, 'interested_genres': ['소설', '과학'],
        })
        self.assertRedirects(response, reverse('books:index'))
        user = User.objects.get(username='newreader')
        self.assertEqual(user.interested_genres, '소설,과학')
        self.assertEqual(user.age, 24)
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertTrue(user.check_password(PASSWORD))

    def test_optional_fields_allow_existing_users(self):
        self.assertEqual(self.user.genre_list, [])
        self.assertIsNone(self.user.age)
        form = CustomUserCreationForm({'username': 'minimal', 'password1': PASSWORD, 'password2': PASSWORD})
        self.assertTrue(form.is_valid(), form.errors)

    def test_positive_integer_validation(self):
        for field in ['age', 'weekly_reading_hours', 'annual_reading_count']:
            for value in [0, -1, '1.5']:
                form = CustomUserChangeForm({'username': self.user.username, field: value}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)
            form = CustomUserChangeForm({'username': self.user.username, field: 1}, instance=self.user)
            self.assertTrue(form.is_valid(), form.errors)

    def test_model_validation_also_rejects_zero(self):
        self.user.age = 0
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_unknown_genre_rejected(self):
        form = CustomUserChangeForm({'username': self.user.username, 'interested_genres': ['unknown']}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('interested_genres', form.errors)

    def test_update_initial_and_genre_serialization(self):
        self.user.interested_genres = '소설,과학'
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:update'))
        self.assertEqual(response.context['form'].initial['interested_genres'], ['소설', '과학'])
        self.assertContains(response, 'form-check-input')
        response = self.client.post(reverse('accounts:update'), {
            'username': self.user.username, 'email': 'changed@example.com', 'interested_genres': ['인문', '예술'],
            'weekly_reading_hours': 3, 'is_superuser': 'true', 'is_staff': 'true',
        })
        self.assertRedirects(response, reverse('books:index'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.interested_genres, '인문,예술')
        self.assertEqual(self.user.weekly_reading_hours, 3)
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)
        self.client.post(reverse('accounts:update'), {'username': self.user.username})
        self.user.refresh_from_db()
        self.assertEqual(self.user.interested_genres, '')

    def test_admin_fields_hidden_and_profile_nav(self):
        fields = CustomUserChangeForm(instance=self.user).fields
        for field in ['password', 'is_superuser', 'is_staff', 'groups', 'user_permissions']:
            self.assertNotIn(field, fields)
        self.client.force_login(self.user)
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, reverse('accounts:profile', args=[self.user.username]))
        self.assertNotContains(response, reverse('accounts:update'))

    def test_profile_displays_all_required_information(self):
        self.user.first_name, self.user.last_name, self.user.gender = '독자', '김', 'female'
        self.user.age, self.user.weekly_reading_hours, self.user.annual_reading_count = 24, 5, 18
        self.user.interested_genres = '소설,과학'
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile', args=[self.user.username]))
        for value in [self.user.username, self.user.email, '김독자', '여성', '24세', '소설', '과학', '주간 평균 독서 시간', '연간 독서량']:
            self.assertContains(response, value)
        self.assertContains(response, reverse('accounts:update'))
        self.assertContains(response, reverse('accounts:delete'))

    def test_other_profile_hides_account_controls_and_escapes_text(self):
        other = User.objects.create_user(username='other', first_name='<script>alert(1)</script>')
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile', args=[other.username]))
        self.assertNotContains(response, reverse('accounts:update'))
        self.assertNotContains(response, reverse('accounts:delete'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_profile_auth_method_and_missing_user(self):
        endpoint = reverse('accounts:profile', args=[self.user.username])
        self.assertEqual(self.client.get(endpoint).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(endpoint).status_code, 405)
        self.assertEqual(self.client.get(reverse('accounts:profile', args=['missing'])).status_code, 404)

    def test_password_change_and_post_only_account_actions(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:change_password'), {
            'old_password': PASSWORD, 'new_password1': 'Changed!Reader_419', 'new_password2': 'Changed!Reader_419',
        })
        self.assertRedirects(response, reverse('books:index'))
        self.assertEqual(self.client.get(reverse('accounts:profile', args=[self.user.username])).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Changed!Reader_419'))
        for name in ['logout', 'delete']:
            self.assertEqual(self.client.get(reverse('accounts:' + name)).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse('accounts:delete')).status_code, 403)
