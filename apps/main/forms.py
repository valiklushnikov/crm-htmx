from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import (
    Employee,
    EmploymentPeriod,
    Document,
    WorkPermit,
    CardSubmission,
    Contract,
    Sanepid,
    Contact,
)


class EmployeeCompleteForm(forms.Form):

    first_name = forms.CharField(
        max_length=128,
        required=True,
        widget=forms.TextInput(
            attrs={
                "id": "firstName",
                "name": "first_name",
                "class": "form-group__input",
                "placeholder": _("Введіть ім'я"),
            }
        ),
    )
    last_name = forms.CharField(
        max_length=128,
        required=True,
        widget=forms.TextInput(
            attrs={
                "id": "lastName",
                "name": "last_name",
                "class": "form-group__input",
                "placeholder": _("Введіть прізвище"),
            }
        ),
    )
    age = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={
                "id": "age",
                "name": "age",
                "class": "form-group__input",
                "placeholder": _("Введіть вік"),
            }
        ),
    )
    is_student = forms.ChoiceField(
        required=False,
        choices=[("true", _("Так")), ("false", _("Ні"))],
        widget=forms.Select(
            attrs={
                "id": "isStudent",
                "name": "isStudent",
                "class": "form-group__select",
            }
        ),
    )
    pesel = forms.CharField(
        max_length=36,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "pesel",
                "name": "pesel",
                "class": "form-group__input",
                "placeholder": _("Введіть Pesel"),
            }
        ),
    )
    pesel_urk = forms.ChoiceField(
        required=False,
        choices=[("true", _("Так")), ("false", _("Ні"))],
        widget=forms.Select(
            attrs={"id": "peselUrk", "name": "peselUrk", "class": "form-group__select"}
        ),
    )
    workplace = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "workplace",
                "name": "workplace",
                "class": "form-group__input",
                "placeholder": _("Введіть місце роботи"),
            }
        ),
    )
    pit_2 = forms.ChoiceField(
        required=False,
        choices=[("true", _("Так")), ("false", _("Ні"))],
        widget=forms.Select(
            attrs={"id": "pit2", "name": "pit2", "class": "form-group__select"}
        ),
    )
    working_status = forms.ChoiceField(
        required=False,
        choices=[
            ("Pracujący", _("Працевлаштований")),
            ("Zwolniony", _("Звільнений")),
            ("Umowa o prace", _("Трудовий договір")),
            ("Zmiana stanowiska", _("Зміна посади")),
        ],
        widget=forms.Select(
            attrs={
                "id": "workingStatus",
                "name": "workingStatus",
                "class": "form-group__select",
            }
        ),
    )

    employment_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "employmentStartDate",
                "name": "employment_start_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )
    employment_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "employmentEndDate",
                "name": "employment_end_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    doc_type = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "docType",
                "name": "doc_type",
                "class": "form-group__input",
                "placeholder": _("Наприклад: karta"),
            }
        ),
    )
    doc_number = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "docNumber",
                "name": "doc_number",
                "class": "form-group__input",
                "placeholder": _("Введіть номер"),
            }
        ),
    )
    doc_valid_until = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "docValidUntil",
                "name": "doc_valid_until",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    work_permit_type = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "workPermitType",
                "name": "work_permit_type",
                "class": "form-group__input",
                "placeholder": _("Введіть тип"),
            }
        ),
    )
    work_permit_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "workPermitEndDate",
                "name": "work_permit_end_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    card_submission_type = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "cardSubmissionType",
                "name": "card_submission_type",
                "class": "form-group__input",
                "placeholder": _("Введіть тип"),
            }
        ),
    )
    card_submission_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "cardSubmissionStartDate",
                "name": "card_submission_start_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    contract_type = forms.ChoiceField(
        required=False,
        choices=[
            ("o_prace", _("Трудовий договір")),
            ("zlecenia", _("Мандатний контракт")),
        ],
        initial="zlecenia",
        widget=forms.Select(
            attrs={
                "id": "contractType",
                "name": "contract_type",
                "class": "form-group__select",
            }
        ),
    )

    sanepid_status = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "sanepidStatus",
                "name": "sanepid_status",
                "class": "form-group__input",
                "placeholder": _("Введіть статус"),
            }
        ),
    )

    contact_type = forms.ChoiceField(
        required=False,
        choices=[
            ("email", _("Телефон")),
            ("phone", _("Email")),
            ("viber", _("Viber")),
        ],
        widget=forms.Select(
            attrs={
                "id": "contactType",
                "name": "contact_type",
                "class": "form-group__select",
            }
        ),
    )
    contact_value = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "contactValue",
                "name": "contact_value",
                "class": "form-group__input",
                "placeholder": _("Введіть контакт"),
            }
        ),
    )

    additional_information = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "id": "additionalInformation",
                "name": "additional_information",
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Введіть додаткову інформацію"),
            }
        ),
    )

    student_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "studentEndDate",
                "name": "student_end_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    sanepid_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "id": "sanepidEndDate",
                "name": "sanepid_end_date",
                "class": "form-group__input",
                "type": "date",
            }
        ),
    )

    def save_to_models(self, employee_id=None):

        data = self.cleaned_data

        if employee_id:
            employee = Employee.objects.get(id=employee_id)
            employee.first_name = data.get('first_name')
            employee.last_name = data.get('last_name')
            employee.age = data.get('age')
            employee.is_student = self._string_to_bool(data.get('is_student'))
            employee.pesel = data.get('pesel')
            employee.pesel_urk = self._string_to_bool(data.get('pesel_urk'))
            employee.workplace = data.get('workplace')
            employee.pit_2 = self._string_to_bool(data.get('pit_2'))
            employee.working_status = data.get('working_status') or None
            employee.additional_information = data.get('additional_information')
            employee.student_end_date = data.get('student_end_date')
            employee.save()
        else:
            employee = Employee.objects.create(
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                age=data.get('age'),
                is_student=self._string_to_bool(data.get('is_student')),
                pesel=data.get('pesel'),
                pesel_urk=self._string_to_bool(data.get('pesel_urk')),
                workplace=data.get('workplace'),
                pit_2=self._string_to_bool(data.get('pit_2')),
                working_status=data.get('working_status') or None,
                additional_information=data.get('additional_information'),
                student_end_date=data.get('student_end_date')
            )

        if data.get('employment_start_date'):
            employment_period, _ = EmploymentPeriod.objects.update_or_create(
                employee=employee,
                defaults={
                    'start_date': data.get('employment_start_date'),
                    'end_date': data.get('employment_end_date'),
                }
            )

        if data.get('doc_type'):
            document, _ = Document.objects.update_or_create(
                employee=employee,
                defaults={
                    'doc_type': data.get('doc_type'),
                    'number': data.get('doc_number'),
                    'valid_until': data.get('doc_valid_until'),
                }
            )

        if data.get('work_permit_type'):
            work_permit, _ = WorkPermit.objects.update_or_create(
                employee=employee,
                defaults={
                    'doc_type': data.get('work_permit_type'),
                    'end_date': data.get('work_permit_end_date'),
                }
            )

        if data.get('card_submission_type'):
            card_submission, _ = CardSubmission.objects.update_or_create(
                employee=employee,
                defaults={
                    'doc_type': data.get('card_submission_type'),
                    'start_date': data.get('card_submission_start_date'),
                }
            )

        if data.get('contract_type'):
            contract, _ = Contract.objects.update_or_create(
                employee=employee,
                defaults={
                    'contract_type': data.get('contract_type'),
                }
            )

        if data.get('sanepid_status'):
            sanepid, _ = Sanepid.objects.update_or_create(
                employee=employee,
                defaults={
                    'status': data.get('sanepid_status'),
                    'doc_type': data.get('sanepid_status'),
                    'end_date': data.get('sanepid_end_date')
                }
            )

        return employee

    @staticmethod
    def _string_to_bool(value):
        if value == 'true':
            return True
        elif value == 'false':
            return False
        return None



ContactFormSet = inlineformset_factory(
    Employee,
    Contact,
    fields=("contact_type", "value"),
    extra=1,
    can_delete=True
)