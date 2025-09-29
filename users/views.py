from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from .forms import CustomUserCreationForm, CustomUserLoginForm, CustomUserUpdateForm, PasswordResetRequestForm, PasswordResetConfirmForm
from .models import CustomUser
from celery import shared_task
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
import logging
from main.models import Perfume
from celery.result import AsyncResult
from django.contrib import messages

logger = logging.getLogger(__name__)

@shared_task
def send_welcome_email(email, first_name):
    subject = "Welcome to Santa Maria Novella!"
    message = f"""
    Hi {first_name},

    Thank you for joining Santa Maria Novella! We're excited to have you with us.
    Explore our exclusive fragrances and enjoy a personalized shopping experience.

    Best regards,
    Santa Maria Novella Team
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        raise

@shared_task
def send_password_reset_email(email, user_id):
    logger.info(f"Starting password reset email task for {email}, user_id={user_id}")
    user = CustomUser.objects.get(pk=user_id)
    logger.info(f"User found: {user.email}")
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = f"{settings.SITE_URL}{reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"
    logger.info(f"Generated reset URL: {reset_url}")
    
    subject = "Password Reset Request"
    message = f"""
    Hi {user.first_name or user.email},

    Please click the link below to reset your password:
    {reset_url}

    If you did not request this, please ignore this email.

    Best regards,
    Santa Maria Novella Team
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        raise

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            send_welcome_email.delay(user.email, user.first_name)
            return redirect('main:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomUserLoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('main:home')
    else:
        form = CustomUserLoginForm()
    return render(request, 'users/login.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')
    else:
        form = CustomUserUpdateForm(instance=request.user)
    
    # Получаем первые три доступных товара
    recommended_perfumes = Perfume.objects.filter(available=True).order_by('id')[:3]
    
    return render(request, 'users/profile.html', {
        'form': form,
        'user': request.user,
        'recommended_perfumes': recommended_perfumes
    })


@login_required
def account_details(request):
    # Обновляем данные пользователя из базы
    user = CustomUser.objects.get(id=request.user.id)
    return render(request, 'users/partials/account_details.html', {'user': user})

@login_required
def edit_account_details(request):
    form = CustomUserUpdateForm(instance=request.user)
    return render(request, 'users/partials/edit_account_details.html', {'user': request.user, 'form': form})

@login_required
def update_account_details(request):
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.clean()  # Применяем очистку данных, как указано в модели
            user.save()
            logger.info(f"User {user.email} updated: {user.country}, {user.address1}, {user.city}")
            # Обновляем объект request.user, чтобы отобразить новые данные
            updated_user = CustomUser.objects.get(id=user.id)
            request.user = updated_user
            return render(request, 'users/partials/account_details.html', {'user': updated_user})
        else:
            logger.error(f"Form validation failed: {form.errors}")
            # Если форма невалидна, возвращаем форму с ошибками
            return render(request, 'users/partials/edit_account_details.html', {'user': request.user, 'form': form})
    return render(request, 'users/partials/account_details.html', {'user': request.user})

def logout_view(request):
    logout(request)
    return redirect('main:home')


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.filter(email=email).first()
            if user:
                logger.info(f"Attempting to send password reset email to {email} for user ID {user.pk}")
                send_password_reset_email.delay(email, user.pk)
                logger.info(f"Password reset email task queued for {email}")
                messages.success(request, "Password reset email has been queued. Please check your inbox or spam folder.")
            else:
                messages.warning(request, "No account found with this email.")
            return render(request, 'users/password_reset_done.html')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'users/password_reset_request.html', {'form': form})


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                return render(request, 'users/password_reset_complete.html')
        else:
            form = PasswordResetConfirmForm()
        return render(request, 'users/password_reset_confirm.html', {'form': form, 'validlink': True})
    else:
        return render(request, 'users/password_reset_confirm.html', {'validlink': False})


# docker run -it --rm --name redis -p 6379:6379 redis
# celery -A novella worker -l info --pool=solo
