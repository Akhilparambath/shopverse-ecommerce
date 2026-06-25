from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_registration_email(self, user_email, username):
    try:
        subject = 'Welcome to ShopVerse!'
        message = f'Hi {username},\n\nThank you for registering at ShopVerse. We are excited to have you on board!'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return 'Registration email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending registration email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_email, reset_url):
    try:
        subject = 'Password Reset Request'
        message = f'You requested a password reset. Please use the following link to reset your password:\n\n{reset_url}'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return 'Password reset email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending password reset email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, user_email, order_id):
    try:
        subject = f'Order Confirmation - {order_id}'
        message = f'Thank you for your order!\n\nYour order {order_id} has been confirmed and is being processed.'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return 'Order confirmation email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending order confirmation email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_payment_notification_email(self, user_email, order_id, status):
    try:
        subject = f'Payment {status} - Order {order_id}'
        message = f'Your payment for order {order_id} was {status}. Thank you!'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return 'Payment notification email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending payment notification email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_shipping_update_email(self, user_email, order_id):
    try:
        subject = f'Order Shipped - {order_id}'
        message = f'Great news! Your order {order_id} has been shipped.'
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,

        )
        return 'Shipping update email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending shipping update email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def send_delivery_confirmation_email(self, user_email, order_id):
    try:
        subject = f'Order Delivered - {order_id}'
        message = f'Your order {order_id} has been delivered. Enjoy!'
        send_mail(
            subject,7





            
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        return 'Delivery confirmation email sent successfully'
    except Exception as exc:
        logger.error(f"Error sending delivery confirmation email to {user_email}: {exc}")
        raise self.retry(exc=exc, countdown=60)
