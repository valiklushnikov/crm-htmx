from django.core.management.base import BaseCommand
from apps.main.models import Employee


class Command(BaseCommand):
    help = "Mark employees status"

    def handle(self, *args, **options):
        employees = Employee.objects.all()
        for employee in employees:
            employee.working_status = "Zwolniony"
            employee.save()

        green_mark = [3,4,5,6,7,9,10,11,13,14,18,19,22,24,27,30,33,35,36,45,51,55,59,63,97,116,147,152,155,157,172,181,184,193,195,202,203,213,216,219,221,223,224,227,228,229,231,235,239,240,241,242,244,245,246,247,248,249,250,251,252,253,254,255,256,257,258,259,260,261,262,263,264,265,266]
        blue_mark = [1,54,230]
        white_mark = [220,243,267,268,269,270,271,272,273,274,275]
        for employee in employees:
            if employee.id in green_mark:
                employee.working_status = "Pracujący"
            elif employee.id in blue_mark:
                employee.working_status = "Umowa o prace"
            elif employee.id in white_mark:
                employee.working_status = "Zmiana stanowiska"
            employee.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Mark instances done!"
            )
        )
