from datetime import date

from dateutil.relativedelta import relativedelta
from django.db.models import Exists, OuterRef

from celery import shared_task

from apps.main.models import Document, WorkPermit
from apps.notification.models import Notification


@shared_task
def check_expiring_documents():
    today = date.today()
    target_date = today + relativedelta(months=2)

    documents = Document.objects.filter(
        valid_until__isnull=False,
        valid_until__gte=today,
        valid_until__lte=target_date
    ).exclude(
        Exists(Notification.objects.filter(document=OuterRef('pk')))
    ).exclude(
            employee__working_status="Zwolniony"
    ).select_related("employee")

    work_permits = WorkPermit.objects.filter(
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=target_date
    ).exclude(
        Exists(Notification.objects.filter(work_permit=OuterRef('pk')))
    ).exclude(
            employee__working_status="Zwolniony"
    ).select_related("employee")

    doc_notifications = [
        Notification(
            notification_type="document",
            employee=doc.employee,
            document=doc,
            days_left=(doc.valid_until - today).days,
            message=(
                f"Документ {doc.doc_type or 'Невідомий'} №{doc.number or 'Не вказано'} "
                f"закінчується через {(doc.valid_until - today).days} днів (до {doc.valid_until})."
            ),
        )
        for doc in documents
    ]

    permit_notifications = [
        Notification(
            notification_type="work_permit",
            employee=permit.employee,
            work_permit=permit,
            days_left=(permit.end_date - today).days,
            message=(
                f"Документ {permit.doc_type or 'Невідомий'} "
                f"закінчується через {(permit.end_date - today).days} днів (до {permit.end_date})."
            ),
        )
        for permit in work_permits
    ]

    if doc_notifications or permit_notifications:
        Notification.objects.bulk_create(
            doc_notifications + permit_notifications)


@shared_task
def decrease_days_left():
    notifications = Notification.objects.select_related("document", "work_permit")

    to_update = []
    to_delete = []

    for n in notifications:
        if n.days_left > 1:
            n.days_left -= 1
            doc_type = "Невідомий"
            doc_number = "Не вказано"

            if n.document:
                doc_type = n.document.doc_type or "Невідомий"
                doc_number = n.document.number or "Не вказано"
            elif n.work_permit:
                doc_type = n.work_permit.doc_type or "Невідомий"

            n.message = f"Документ {doc_type} № {doc_number} мине через {n.days_left} днів."
            to_update.append(n)
        else:
            to_delete.append(n.id)

    if to_update:
        Notification.objects.bulk_update(to_update, ['days_left', 'message'])

    if to_delete:
        Notification.objects.filter(id__in=to_delete).delete()