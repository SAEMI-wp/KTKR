# 인증 관련 뷰들
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django import forms

from ..models import Employee
from ..forms import SignupForm


# ログインビュー
def login_view(request):
    if request.user.is_authenticated:
        return redirect('attendance:main')
    
    from django import forms
    from django.contrib.auth import authenticate
    
    class EmployeeAuthenticationForm(forms.Form):
        employee_no = forms.CharField(label='社員番号', max_length=6)
        password = forms.CharField(label='パスワード', widget=forms.PasswordInput)
        
        def __init__(self, request=None, *args, **kwargs):
            self.request = request
            self.user_cache = None
            super().__init__(*args, **kwargs)
        
        def clean(self):
            employee_no = self.cleaned_data.get('employee_no')
            password = self.cleaned_data.get('password')
            if employee_no and password:
                self.user_cache = authenticate(self.request, employee_no=employee_no, password=password)
                if self.user_cache is None:
                    raise forms.ValidationError('社員番号またはパスワードが正しくありません。')
            return self.cleaned_data
        
        def get_user(self):
            return self.user_cache
    
    if request.method == 'POST':
        form = EmployeeAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'attendance:main')
                return redirect(next_url)
    else:
        form = EmployeeAuthenticationForm()
    
    return render(request, 'attendance/login.html', {'form': form})


# ログアウトビュー
@login_required
def logout_view(request):
    logout(request)
    return redirect('attendance:login')


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(label='現在のパスワード', widget=forms.PasswordInput)
    new_password1 = forms.CharField(label='新しいパスワード', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='新しいパスワード（確認）', widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError('現在のパスワードが正しくありません。')
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get('new_password1')
        pw2 = cleaned_data.get('new_password2')
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError('新しいパスワードが一致しません。')
        return cleaned_data


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password1'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'パスワードを変更しました。再度ログインしてください。')
            return redirect('attendance:login')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'attendance/password_change.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            employee_no = form.cleaned_data['employee_no']
            password = form.cleaned_data['password']
            if Employee.objects.filter(employee_no=employee_no).exists():
                messages.error(request, 'この社員番号は既に登録されています。')
            else:
                user = Employee(employee_no=employee_no)
                user.set_password(password)
                user.save()
                messages.success(request, 'ユーザー登録が完了しました。ログインしてください。')
                return redirect('/')
    else:
        form = SignupForm()
    return render(request, 'attendance/signup.html', {'form': form}) 