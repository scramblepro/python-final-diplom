from typing import Type
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import User

new_user_registered = Signal()
new_order = Signal()


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    msg = EmailMultiAlternatives(
        f"Password Reset Token for {reset_password_token.user}",
        reset_password_token.key,
        settings.EMAIL_HOST_USER,
        [reset_password_token.user.email]
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_signal(sender: Type[User], instance: User, created: bool, **kwargs):
    if created and not instance.is_active and not instance.confirmation_token:
        import uuid
        instance.confirmation_token = uuid.uuid4().hex
        instance.save(update_fields=['confirmation_token'])

        msg = EmailMultiAlternatives(
            f"Email confirmation for {instance.email}",
            instance.confirmation_token,
            settings.EMAIL_HOST_USER,
            [instance.email]
        )
        msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    from backend.models import Order  # чтобы не было циклического импорта
    user = User.objects.get(id=user_id)
    msg = EmailMultiAlternatives(
        f"Обновление статуса заказа",
        'Заказ сформирован',
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg.send()
