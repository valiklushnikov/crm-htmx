"""Utility functions for checking document expiry and creating notifications."""
from datetime import date
from dateutil.relativedelta import relativedelta

from apps.notification.models import Notification


def check_and_create_notifications(employee):
    """
    Check all documents and work permits for the given employee and create
    notifications for those expiring within 2 months.

    Args:
        employee: Employee instance to check documents for
    """
    if employee.working_status == "Zwolniony":
        return

    today = date.today()
    target_date = today + relativedelta(months=2)

    # Check Document objects
    documents = employee.documents.filter(
        valid_until__isnull=False,
        valid_until__gte=today,
        valid_until__lte=target_date
    )

    for doc in documents:
        # Check if notification already exists
        if not Notification.objects.filter(
            document=doc,
            employee=employee
        ).exists():
            days_left = (doc.valid_until - today).days
            doc_type = doc.doc_type or "Невідомий"
            doc_number = doc.number or "Не вказано"

            message = (
                f"Документ {doc_type} №{doc_number} "
                f"закінчується через {days_left} днів (до {doc.valid_until})"
            )

            Notification.objects.create(
                notification_type="document",
                employee=employee,
                document=doc,
                days_left=days_left,
                message=message
            )

    # Check WorkPermit objects
    work_permits = employee.work_permits.filter(
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=target_date
    )

    for permit in work_permits:
        # Check if notification already exists
        if not Notification.objects.filter(
            work_permit=permit,
            employee=employee
        ).exists():
            days_left = (permit.end_date - today).days
            doc_type = permit.doc_type or "Невідомий"

            message = (
                f"Документ {doc_type} "
                f"закінчується через {days_left} днів (до {permit.end_date})"
            )

            Notification.objects.create(
                notification_type="work_permit",
                employee=employee,
                work_permit=permit,
                days_left=days_left,
                message=message
            )
