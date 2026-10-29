from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import BookForm
from .models import Book
from .services import AuthorInfoError, generate_author_info


@require_GET
def index(request):
    books = Book.objects.order_by('-pk')
    return render(request, 'books/index.html', {'books': books})


@require_GET
def detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'books/detail.html', {'book': book})


def save_author_info(request, book):
    try:
        data = generate_author_info(book.author, book.title)
        for field, value in data.items():
            setattr(book, field, value)
        book.author_generated_at = timezone.now()
        book.save(update_fields=[*data, 'author_generated_at'])
        messages.success(request, '작가 정보와 대표작을 생성했습니다.')
    except AuthorInfoError as exc:
        messages.warning(request, f'도서 정보는 저장되어 있습니다. {exc}')


@require_http_methods(['GET', 'POST'])
@login_required(login_url='accounts:login')
def create(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            messages.success(request, '도서를 등록했습니다.')
            if form.cleaned_data['generate_author']:
                save_author_info(request, book)
            return redirect('books:detail', pk=book.pk)
    else:
        form = BookForm()
    return render(request, 'books/form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@login_required(login_url='accounts:login')
def update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    original_author = book.author
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            book = form.save(commit=False)
            if original_author != book.author:
                book.author_info, book.author_works = '', []
                book.author_photo, book.author_source, book.author_generated_at = '', '', None
            book.save()
            messages.success(request, '도서 정보를 수정했습니다.')
            if form.cleaned_data['generate_author']:
                save_author_info(request, book)
            return redirect('books:detail', pk=book.pk)
    else:
        form = BookForm(instance=book)
    return render(request, 'books/form.html', {'form': form, 'book': book})


@require_POST
@login_required(login_url='accounts:login')
def delete(request, pk):
    get_object_or_404(Book, pk=pk).delete()
    return redirect('books:index')


@require_POST
@login_required(login_url='accounts:login')
def generate_author(request, pk):
    book = get_object_or_404(Book, pk=pk)
    save_author_info(request, book)
    return redirect('books:detail', pk=book.pk)
