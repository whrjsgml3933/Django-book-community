from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import CustomUserCreationForm, CustomUserChangeForm


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.user.is_authenticated:
        return redirect('books:index')
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('books:index')
    else:
        form = AuthenticationForm(request)
    return render(request, 'accounts/login.html', {'form': form})


@require_POST
@login_required(login_url='accounts:login')
def logout(request):
    auth_logout(request)
    return redirect('books:index')


@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('books:index')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.interested_genres = ','.join(form.cleaned_data['interested_genres'])
            user.save()
            auth_login(request, user)
            messages.success(request, '회원가입이 완료되었습니다. 내 프로필에서 독서 정보를 확인해 보세요.')
            return redirect('books:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})


@require_POST
@login_required(login_url='accounts:login')
def delete(request):
    request.user.delete()
    auth_logout(request)
    return redirect('books:index')


@require_http_methods(['GET', 'POST'])
@login_required(login_url='accounts:login')
def update(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.interested_genres = ','.join(form.cleaned_data['interested_genres'])
            user.save()
            messages.success(request, '회원정보와 독서 취향을 저장했습니다.')
            return redirect('books:index')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'accounts/update.html', {'form': form})


@require_http_methods(['GET', 'POST'])
@login_required(login_url='accounts:login')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '비밀번호가 변경되었습니다.')
            return redirect('books:index')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@require_GET
@login_required(login_url='accounts:login')
def profile(request, username):
    person = get_object_or_404(get_user_model(), username=username)
    return render(request, 'accounts/profile.html', {'person': person})
