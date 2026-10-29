import json
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from .forms import BookForm
from .models import Book
from .services import AuthorInfoError, generate_author_info


AUTHOR_DATA = {'author_info': '검색 자료를 바탕으로 작성한 작가 소개입니다.', 'author_works': ['대표 작품'], 'author_photo': 'https://upload.wikimedia.org/example.jpg', 'author_source': 'https://ko.wikipedia.org/wiki/example'}
WIKI = {'query': {'pages': [{'index': 1, 'title': '작가', 'extract': '실제 작가의 소개', 'fullurl': 'https://ko.wikipedia.org/wiki/example', 'thumbnail': {'source': 'https://upload.wikimedia.org/example.jpg'}}]}}


def completion(data=None, finish='stop'):
    data = data if data is not None else {'matched': True, 'source_index': 0, 'author_info': '소개', 'author_works': ['작품']}
    return {'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(data)}}]}


@override_settings(GMS_API_KEY='test-key-only', GMS_API_URL='https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions')
class AuthorServiceTests(SimpleTestCase):
    @patch('books.services.fetch_json', side_effect=[WIKI, completion()])
    def test_wikipedia_then_gms_and_fixed_model(self, fetch):
        result = generate_author_info('작가', '도서')
        self.assertEqual(result['author_info'], '소개')
        self.assertEqual(result['author_works'], ['작품'])
        self.assertTrue(result['author_photo'].startswith('https://'))
        self.assertIn('ko.wikipedia.org/w/api.php?', fetch.call_args_list[0].args[0])
        payload = fetch.call_args_list[1].kwargs['payload']
        self.assertEqual(payload['model'], 'gpt-5-nano')
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertNotIn('temperature', payload)
        self.assertIn('실제 작가의 소개', payload['messages'][1]['content'])

    @override_settings(GMS_API_KEY='')
    @patch('books.services.fetch_json')
    def test_missing_key_does_not_call_network(self, fetch):
        with self.assertRaises(AuthorInfoError):
            generate_author_info('작가', '도서')
        fetch.assert_not_called()

    @override_settings(GMS_API_URL='http://example.com/')
    @patch('books.services.fetch_json')
    def test_https_required(self, fetch):
        with self.assertRaises(AuthorInfoError):
            generate_author_info('작가', '도서')
        fetch.assert_not_called()

    def test_invalid_json_schema_rejected(self):
        bad = [
            {'matched': False},
            {'matched': True, 'source_index': True, 'author_info': '소개', 'author_works': []},
            {'matched': True, 'source_index': 9, 'author_info': '소개', 'author_works': []},
            {'matched': True, 'source_index': 0, 'author_info': '', 'author_works': []},
            {'matched': True, 'source_index': 0, 'author_info': '소개', 'author_works': '작품'},
            {'matched': True, 'source_index': 0, 'author_info': '소개', 'author_works': [7]},
            {'matched': True, 'source_index': 0, 'author_info': '소개', 'author_works': ['작품'] * 6},
        ]
        for data in bad:
            with self.subTest(data=data), patch('books.services.fetch_json', side_effect=[WIKI, completion(data)]):
                with self.assertRaises(AuthorInfoError):
                    generate_author_info('작가', '도서')

    def test_truncated_and_malformed_response_rejected(self):
        for answer in [completion(finish='length'), {'choices': []}, {'choices': [{'finish_reason': 'stop', 'message': {'content': 'not JSON'}}]}]:
            with patch('books.services.fetch_json', side_effect=[WIKI, answer]):
                with self.assertRaises(AuthorInfoError):
                    generate_author_info('작가', '도서')

    def test_network_errors_and_empty_wiki(self):
        for effects in [[URLError('offline')], [TimeoutError()], [{}], [HTTPError('https://example.com', 401, 'Denied', {}, None)], [WIKI, HTTPError('https://example.com', 429, 'Limit', {}, None)]]:
            with patch('books.services.fetch_json', side_effect=effects):
                with self.assertRaises(AuthorInfoError):
                    generate_author_info('작가', '도서')


@override_settings(GMS_API_KEY='test-key-only')
class AuthorViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='reader', password='Reader!Thread_417')
        self.book = Book.objects.create(title='기존 도서', content='소개', author='기존 작가', star_avg='4.50')
        self.payload = {'title': '새 도서', 'content': '새 소개', 'author': '새 작가', 'star_avg': '4.75'}
        self.client.force_login(self.user)

    @patch('books.views.generate_author_info', return_value=AUTHOR_DATA)
    def test_create_generates_and_stores_author_information(self, generate):
        response = self.client.post(reverse('books:create'), {**self.payload, 'generate_author': 'on'}, follow=True)
        book = Book.objects.get(title='새 도서')
        generate.assert_called_once_with('새 작가', '새 도서')
        self.assertEqual(book.author_info, AUTHOR_DATA['author_info'])
        self.assertEqual(book.author_works, ['대표 작품'])
        self.assertIsNotNone(book.author_generated_at)
        self.assertContains(response, '정확하지 않을 수 있습니다.')
        self.assertContains(response, '대표 작품')
        self.assertEqual(response.redirect_chain[-1][0], reverse('books:detail', args=[book.pk]))

    @patch('books.views.generate_author_info')
    def test_checkbox_opt_out_avoids_network(self, generate):
        self.client.post(reverse('books:create'), self.payload)
        generate.assert_not_called()
        self.assertTrue(Book.objects.filter(title='새 도서').exists())

    @patch('books.views.generate_author_info', side_effect=AuthorInfoError('연결 실패'))
    def test_failed_generation_preserves_book_and_shows_warning(self, generate):
        response = self.client.post(reverse('books:create'), {**self.payload, 'generate_author': 'on'}, follow=True)
        self.assertTrue(Book.objects.filter(title='새 도서').exists())
        self.assertContains(response, '도서 정보는 저장되어 있습니다.')
        self.assertContains(response, '연결 실패')

    @patch('books.views.generate_author_info', return_value=AUTHOR_DATA)
    def test_retry_endpoint_requires_auth_post_and_csrf(self, generate):
        endpoint = reverse('books:generate_author', args=[self.book.pk])
        self.assertEqual(self.client.get(endpoint).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(endpoint).status_code, 302)
        generate.assert_not_called()
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post(endpoint), reverse('books:detail', args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.author_info, AUTHOR_DATA['author_info'])

    @patch('books.views.generate_author_info')
    def test_author_change_clears_previous_person_data(self, generate):
        for field, value in AUTHOR_DATA.items():
            setattr(self.book, field, value)
        self.book.save()
        response = self.client.post(reverse('books:update', args=[self.book.pk]), self.payload)
        self.assertRedirects(response, reverse('books:detail', args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.author_info, '')
        self.assertEqual(self.book.author_works, [])
        self.assertEqual(self.book.author_photo, '')
        self.assertIsNone(self.book.author_generated_at)
        generate.assert_not_called()

    @patch('books.views.generate_author_info')
    def test_invalid_form_does_not_generate(self, generate):
        response = self.client.post(reverse('books:create'), {'generate_author': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Book.objects.count(), 1)
        generate.assert_not_called()

    def test_registration_default_depends_on_key_and_existing_book(self):
        self.assertTrue(BookForm().fields['generate_author'].initial)
        self.assertFalse(BookForm(instance=self.book).fields['generate_author'].initial)
        with override_settings(GMS_API_KEY=''):
            self.assertFalse(BookForm().fields['generate_author'].initial)

    def test_book_crud_and_escape_still_work(self):
        response = self.client.post(reverse('books:create'), self.payload)
        book = Book.objects.get(title='새 도서')
        self.assertRedirects(response, reverse('books:detail', args=[book.pk]))
        self.assertContains(self.client.get(reverse('books:index')), book.title)
        book.author_info = '<script>alert(1)</script>'
        book.save()
        self.assertContains(self.client.get(reverse('books:detail', args=[book.pk])), '&lt;script&gt;')
        self.assertEqual(self.client.get(reverse('books:delete', args=[book.pk])).status_code, 405)
        self.assertRedirects(self.client.post(reverse('books:delete', args=[book.pk])), reverse('books:index'))
        self.assertFalse(Book.objects.filter(pk=book.pk).exists())
