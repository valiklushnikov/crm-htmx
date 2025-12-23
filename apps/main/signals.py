from django.utils.timezone import now
from dateutil.relativedelta import relativedelta
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from .models import Employee, History, Document, WorkPermit
from apps.notification.models import Notification
from .utils import get_change_user


@receiver(post_save, sender=Employee)
def log_post_save(sender, instance, created, **kwargs):
    if created:
        ct = ContentType.objects.get_for_model(sender)
        user = get_change_user()

        History.objects.create(
            content_type=ct,
            object_id=instance.pk,
            field_name='__all__',
            changed_by=user,
            action="created"
        )


@receiver(post_delete, sender=Employee)
def log_post_delete(sender, instance, **kwargs):
    ct = ContentType.objects.get_for_model(sender)
    user = get_change_user()

    History.objects.create(
        content_type=ct,
        object_id=instance.pk,
        field_name='__all__',
        old_value=str(instance),
        changed_by=user,
        action="deleted"
    )

@receiver([post_save, post_delete], sender=Employee)
def invalidate_employee_cache(sender, instance, **kwargs):
    cache.clear()


@receiver([post_save], sender=Employee)
def delete_notification_working_status(sender, instance, **kwargs):
    if instance.working_status == "Zwolniony":
        notifications = Notification.objects.filter(employee=instance)
        notifications.delete()


@receiver(post_save, sender=Document)
def delete_notifications_if_document_valid(sender, instance, **kwargs):
    today = now().date()
    limit_date = today + relativedelta(months=2)

    if not instance.valid_until or instance.employee.working_status == "Zwolniony":
        Notification.objects.filter(document=instance).delete()
        return

    if instance.valid_until.date() > limit_date:
        Notification.objects.filter(document=instance).delete()


@receiver(post_save, sender=WorkPermit)
def delete_notifications_if_permit_valid(sender, instance, **kwargs):
    today = now().date()
    limit_date = today + relativedelta(months=2)

    if not instance.end_date or instance.employee.working_status == "Zwolniony":
        Notification.objects.filter(work_permit=instance).delete()
        return

    if instance.end_date.date() > limit_date:
        Notification.objects.filter(work_permit=instance).delete()
