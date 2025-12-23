from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from apps.main.models import Document, WorkPermit
from apps.notification.models import Notification
from django.db.models import Exists, OuterRef


class Command(BaseCommand):
    help = "Notifications employees documents"

    def handle(self, *args, **options):
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Created notifications: {len(doc_notifications)} documents and {len(permit_notifications)} work permits"
            )
        )
