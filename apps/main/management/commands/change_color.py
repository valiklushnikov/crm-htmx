from django.core.management.base import BaseCommand
from apps.main.models import Employee


class Command(BaseCommand):
    help = "Mark employees status"

    def handle(self, *args, **options):

        color_mapper = {
            "0080004D": "Pracujący",
            "FFA5004D": "Zwolniony",
            "0000FF4D": "Umowa o prace",
            "FFFFFF4D": "Zmiana stanowiska",
        }
        employees = Employee.objects.all()
        for employee in employees:
            employee.working_status = color_mapper[employee.working_status]
            employee.save()
