from django.db import models
from django.db.models import Min, Max


class EmployeeQuerySet(models.QuerySet):
    def base_select(self):
        return self.only(
            "id", "first_name", "last_name", "age", "is_student",
            "pesel", "pesel_urk", "workplace", "pit_2",
            "working_status", "additional_information",
        )

    def with_period_annotations(self):
        return self.annotate(
            earliest_start_date=Min("employment_period__start_date"),
            latest_end_date=Max("employment_period__end_date"),
        )
