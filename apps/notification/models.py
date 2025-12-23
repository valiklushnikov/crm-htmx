from django.db import models
from apps.main.models import Employee, Document, WorkPermit


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("document", "Document"),
        ("work_permit", "Work Permit"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="notifications"
    )

    notification_type = models.CharField(max_length=32, choices=NOTIFICATION_TYPES)

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    work_permit = models.ForeignKey(
        WorkPermit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    message = models.CharField(max_length=255, null=True, blank=True)
    days_left = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (f"У працівника {self.employee.get_full_name}, закінчується термін дії документу "
                f"{self.document if self.document else self.work_permit} через {self.days_left} днів")
