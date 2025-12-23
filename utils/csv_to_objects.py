import re
from datetime import datetime

from django.utils.timezone import make_aware, now

from apps.main.models import Employee, Document, EmploymentPeriod, Contract, Sanepid, WorkPermit, CardSubmission, Contact
import pandas as pd


def create_employee_from_row(row: dict):
    # -------------------------------
    # 1. Разбор имени
    # -------------------------------
    raw_name = row.get("Призвіще", "")
    parts = raw_name.split()
    if len(parts) >= 2:
        first_name = parts[1]
        last_name = parts[0]
    else:
        first_name = raw_name
        last_name = ""

    # -------------------------------
    # 2. Создаем Employee
    # -------------------------------
    employee = Employee.objects.create(
        first_name=first_name,
        last_name=last_name,
        age=row.get("Вік") if row.get("Вік") not in ["", None] else None,
        is_student=bool(row.get("Студент")),
        pesel=row.get("Песель"),
        pesel_urk=True if row.get("UKR") else False,
        workplace=row.get("Місце затруднення"),
        pit_2=bool(row.get("Пит-2")),
        created_at=now(),
        updated_at=now(),
    )
    # -------------------------------
    # 3. EmploymentPeriod
    # -------------------------------
    start_date = row.get("Від")
    end_date = row.get("До")

    if start_date:
        EmploymentPeriod.objects.create(
            employee=employee,
            start_date=start_date,
            end_date=end_date if end_date not in ["", None] else None
        )

    # -------------------------------
    # 4. Document (Підстава + срок действия)
    # -------------------------------
    basis = row.get("Підстава")
    valid_until = row.get("Термін документу")
    if basis:
        basis = basis
    else:
        basis = None

    if basis:
        if basis.lower().startswith("karta"):
            doc_number = basis.replace("karta", "").strip()
            Document.objects.create(
                employee=employee,
                doc_type="karta",
                number=doc_number,
                valid_until=valid_until
            )
        else:
            Document.objects.create(
                employee=employee,
                doc_type=basis.lower().strip(),
                valid_until=valid_until
            )
    else:
        Document.objects.create(
            employee=employee,
            doc_type=None,
            valid_until=None
        )

    # -------------------------------
    # 5. Contract
    # -------------------------------
    contract_type_map = {
        "o prace": "o_prace",
        "zlecenia": "zlecenia"
    }

    contract_type = contract_type_map.get(row.get("Вид умови"))
    if contract_type:
        inst = Contract.objects.create(
            employee=employee,
            contract_type=contract_type,
        )
    # -------------------------------
    # 6. Sanepid
    # -------------------------------
    sanepid = row.get("Sanepid")
    if sanepid:
        Sanepid.objects.create(
            employee=employee,
            status=sanepid.lower().strip(),
            doc_type=sanepid.lower().strip()
        )

    # -------------------------------
    # 7. Work Permit
    # -------------------------------
    permit = row.get("Дозвіл на роботу")
    if permit:
        clean_permit = [i.strip() for i in permit.split(sep="do")]
        if len(clean_permit) >= 2:
            permit_doc = clean_permit[0]
            permit_date = parse_date_field(clean_permit[1])
        else:
            permit_doc = clean_permit[0]
            permit_date = None

        WorkPermit.objects.create(
            employee=employee,
            doc_type=permit_doc,
            end_date=permit_date,
        )

    # -------------------------------
    # 8. Card Submission
    # -------------------------------
    submission = row.get("Подача на карту")
    submission_date = row.get("Дата")

    if submission:
        CardSubmission.objects.create(
            employee=employee,
            doc_type=submission,
            start_date=submission_date,
        )

    # -------------------------------
    # 8. Contacts
    # -------------------------------
    contact = row.get("Контакт")
    if contact:
        ctype, value = parse_contact(contact)
        Contact.objects.create(
            employee=employee,
            contact_type=ctype,
            value=value,
        )


    return employee


def clean_row(row):
    if isinstance(row, pd.Series):
        row = row.to_dict()

    cleaned = {}

    for k, v in row.items():
        # NaN → None
        if isinstance(v, float) and pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v

    return cleaned

def parse_date_field(value):
    if isinstance(value, str):
        if value.strip() == "":
            return None
        value = value.strip()
        date_pattern = re.compile(r"^\d{2}\.\d{2}\.\d{4}$|^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$")
        if date_pattern.match(value):
            if date_pattern.match(value):
                if "." in value:
                    fmt = "%d.%m.%Y"
                elif "-" in value:
                    fmt = "%Y-%m-%d"
                elif "/" in value:
                    fmt = "%d/%m/%Y"
            dt = datetime.strptime(value, fmt)
            return make_aware(dt)
        return value
    return value


def clean_and_parse_row(row):
    if isinstance(row, pd.Series):
        row = row.to_dict()

    cleaned = {}
    date_fields = {"Від", "До", "Дата", "Термін документу"}

    for k, v in row.items():
        # NaN → None
        if isinstance(v, float) and pd.isna(v):
            cleaned[k] = None
            continue

        # Попытка распарсить дату только для известных полей
        if k in date_fields and isinstance(v, str):
            v = v.strip()
            if v == "":
                cleaned[k] = None
                continue

            formats = ["%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
            parsed = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(v, fmt)
                    parsed = make_aware(dt)
                    break  # нашли подходящий формат → выходим
                except ValueError:
                    continue

            if parsed:
                cleaned[k] = parsed
                continue  # строка успешно распарсилась → не сохраняем как текст

        # Всё остальное оставляем как есть
        cleaned[k] = v

    return cleaned

def parse_contact(contact_str):
    if "@" in contact_str:
        return "email", contact_str.strip()

    parts = contact_str.split()
    if len(parts) == 2:
        return parts[0], parts[1]   # 'viber', '+48453172686'

    return None, None
