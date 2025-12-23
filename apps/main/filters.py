from datetime import date

import django_filters
from django import forms
from django.db.models import Q, Min, Max, F, Case, When, IntegerField
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from .models import Employee


class EmployeeMultiFilter(django_filters.FilterSet):
    STATUS_CHOICES = [
        ("pracujący", _("Працевлаштований")),
        ("zwolniony", _("Звільнений")),
        ("umowa_o_prace", _("Трудовий договір")),
        ("zmiana_stanowiska", _("Зміна посади")),
        ("student", _("Студент")),
        ("pit", _("PIT-2")),
    ]

    q = django_filters.CharFilter(
        method="filter_by_name",
        label=_("Пошук"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Імʼя або прізвище")}
        ),
    )

    status = django_filters.MultipleChoiceFilter(
        label=_("Статус"),
        choices=STATUS_CHOICES,
        method="filter_by_status",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ('last_name', 'last_name'),
            ('earliest_start_date', 'start_date'),
            ('latest_end_date', 'end_date'),
            ('id', 'id')
        ),
        method='filter_ordering'
    )

    class Meta:
        model = Employee
        fields = ["status", "q", "ordering"]

    def filter_by_status(self, queryset, name, value):
        if not value:
            return queryset

        status_mapping = {
            "pracujący": "Pracujący",
            "zwolniony": "Zwolniony",
            "umowa_o_prace": "Umowa o prace",
            "zmiana_stanowiska": "Zmiana stanowiska",
        }

        is_student_filter = "student" in value
        is_pit_filter = "pit" in value
        status_filters = [v for v in value if v in status_mapping]

        filters = []

        if is_student_filter:
            filters.append(Q(is_student=True))
        
        if is_pit_filter:
            filters.append(Q(pit_2=True))

        if status_filters:
            status_q = Q()
            for v in status_filters:
                status_q |= Q(working_status=status_mapping[v])
            filters.append(status_q)

        if filters:
            combined_filter = filters[0]
            for f in filters[1:]:
                combined_filter &= f
            return queryset.filter(combined_filter).distinct()
        
        return queryset.distinct()

    def filter_by_name(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )

    def filter_ordering(self, queryset, name, value):
        if not value:
            return queryset

        # Get the ordering filter to access param_map
        ordering_filter = self.filters['ordering']

        # Map user-facing field names to actual field names
        mapped_values = []
        for v in value:
            is_descending = v.startswith('-')
            field_name = v.lstrip('-')

            # Use param_map to get the actual field name
            actual_field = ordering_filter.param_map.get(
                field_name, field_name
            )

            # Add back the descending prefix if needed
            if is_descending:
                actual_field = f'-{actual_field}'

            mapped_values.append(actual_field)

        # Check if we need annotations for date fields
        ordering_fields = [v.lstrip('-') for v in mapped_values]
        needs_annotation = (
            'earliest_start_date' in ordering_fields or
            'latest_end_date' in ordering_fields
        )

        if needs_annotation:
            queryset = queryset.annotate(
                earliest_start_date=Min('employment_period__start_date'),
                latest_end_date=Max('employment_period__end_date')
            )
        
        if 'status_priority' not in queryset.query.annotations:
            queryset = queryset.annotate(
                status_priority=Case(
                    When(working_status='Zwolniony', then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )

        # Build ordering with nulls last for date fields
        ordering_list = ['status_priority']
        for field in mapped_values:
            is_desc = field.startswith('-')
            clean_field = field.lstrip('-')

            # For date fields, put nulls last
            if clean_field in ['earliest_start_date', 'latest_end_date']:
                # Use a far future date for nulls when ascending
                # Use a far past date for nulls when descending
                if is_desc:
                    # Descending: nulls should be last (use min date)
                    null_value = date(1900, 1, 1)
                    ordering_list.append(
                        Coalesce(F(clean_field), null_value).desc()
                    )
                else:
                    # Ascending: nulls should be last (use max date)
                    null_value = date(9999, 12, 31)
                    ordering_list.append(
                        Coalesce(F(clean_field), null_value).asc()
                    )
            else:
                ordering_list.append(field)

        # Add secondary ordering by id for stable pagination
        ordering_list.append('-id')

        return queryset.order_by(*ordering_list)
