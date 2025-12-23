from datetime import date, datetime
import os
import subprocess
from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Min, Max
from django.contrib.contenttypes.models import ContentType
from io import BytesIO
import logging

from apps.main.models import Employee, EmploymentPeriod, History
from apps.users.models import User
from apps.main.filters import EmployeeMultiFilter


logger = logging.getLogger(__name__)


@shared_task
def mark_working_status():
    today = date.today()
    
    employee_ids = EmploymentPeriod.objects.filter(
        end_date__isnull=False,
        end_date__lt=today
    ).values_list("employee_id", flat=True).distinct()

    employees_to_update = Employee.objects.filter(
        id__in=employee_ids
    ).exclude(working_status="Zwolniony")

    employees_data = []
    for emp in employees_to_update:
        old_value = emp._prepare_value(emp.working_status) if hasattr(emp, '_prepare_value') else (emp.working_status or '')
        employees_data.append({
            'id': emp.id,
            'old_value': old_value
        })

    employees_to_update.update(working_status="Zwolniony")

    user = User.objects.get(id=1)
  
    if employees_data:
        ct = ContentType.objects.get_for_model(Employee)
        
        history_entries = [
            History(
                content_type=ct,
                object_id=emp_data['id'],
                field_name='working_status',
                old_value=emp_data['old_value'],
                new_value='Zwolniony',
                changed_by=user,
                action="updated"
            )
            for emp_data in employees_data
        ]
        
        History.objects.bulk_create(history_entries)


@shared_task
def generate_employees_pdf_task(filter_params):
    """
    Celery task для генерації PDF зі списком співробітників
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER

    try:
        logger.info("Starting PDF generation task")


        # Визначаємо мову з параметрів (за замовчуванням українська)
        language = filter_params.get('language', 'uk')
        
        employee_status_map = {
            'uk': {
                "pracujący": "'Працевлаштовані'",
                "zwolniony": "'Звільнені'",
                "umowa_o_prace": "'Трудовий договір'",
                "zmiana_stanowiska": "'Зміна посади'",
                "student": "'Студенти'",
                "pit": "'PIT-2'",
            },
            'pl': {
                "pracujący": "'Pracujący'",
                "zwolniony": "'Zwolniony'",
                "umowa_o_prace": "'Umowa o prace'",
                "zmiana_stanowiska": "'Zmiana_stanowiska'",
                "student": "'Studenci'",
                "pit": "'PIT-2'",
            }
        }

        employees_filter = filter_params.get('status', '')

        if isinstance(employees_filter, list):
            employees_filter_title = ", ".join(
                employee_status_map.get(language, {}).get(item, item)
                for item in employees_filter
            )
        else:
            employees_filter_title = employee_status_map.get(
                language, {}).get(employees_filter, '')
        
        # Реєструємо шрифт DejaVu Sans для підтримки кирилиці
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        except Exception as e:
            logger.warning(f"Could not register DejaVu fonts: {e}")
        
        # Отримуємо відфільтрований queryset
        queryset = Employee.objects.all().select_related().prefetch_related(
            'employment_period',
            'documents',
            'work_permits',
            'contracts',
            'contacts'
        ).annotate(
            earliest_start_date=Min('employment_period__start_date'),
            latest_end_date=Max('employment_period__end_date')
        ).order_by('id')  # Сортуємо за ID для збереження порядку з бази
        
        # Застосовуємо фільтри
        filterset = EmployeeMultiFilter(filter_params, queryset=queryset)
        employees = filterset.qs.order_by('id')  # Зберігаємо сортування після фільтрації
        
        logger.info(f"Generating PDF for {employees.count()} employees")
        
        # Створюємо PDF
        buffer = BytesIO()
        pdf_doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        # Стилі
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='DejaVuSans-Bold',
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        # Переклади
        translations = {
            'uk': {
                'title': 'Список співробітників ' + employees_filter_title,
                'date_label': 'Дата формування',
                'total_label': 'Всього співробітників',
                'headers': ['№', 'Прізвище', "Ім'я", 'Вік', 'Місце роботи', 'Статус',
                           'PESEL', 'Студент', 'Період роботи', 'Документи',
                           'Дозвіл на роботу', 'Контракт', 'Контакти'],
                'yes': 'Так',
                'no': 'Ні',
                'status_map': {
                    'Pracujący': 'Працевлаштований',
                    'Zwolniony': 'Звільнений',
                    'Umowa o prace': 'Трудовий договір',
                    'Zmiana stanowiska': 'Зміна посади'
                }
            },
            'pl': {
                'title': 'Lista pracowników ' + employees_filter_title,
                'date_label': 'Data utworzenia',
                'total_label': 'Łącznie pracowników',
                'headers': ['№', 'Nazwisko', 'Imię', 'Wiek', 'Miejsce pracy', 'Status',
                           'PESEL', 'Student', 'Okres pracy', 'Dokumenty',
                           'Zezwolenie na pracę', 'Umowa', 'Kontakty'],
                'yes': 'Tak',
                'no': 'Nie',
                'status_map': {
                    'Pracujący': 'Pracujący',
                    'Zwolniony': 'Zwolniony',
                    'Umowa o prace': 'Umowa o prace',
                    'Zmiana stanowiska': 'Zmiana stanowiska'
                }
            }
        }

        # Вибираємо переклади для поточної мови
        t = translations.get(language, translations['uk'])

        # Елементи документа
        elements = []

        # Заголовок
        title = Paragraph(t['title'], title_style)
        elements.append(title)

        # Мета-інформація
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=7,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )
        meta_text = f"{t['date_label']}: {timezone.now().strftime('%d.%m.%Y %H:%M')} | {t['total_label']}: {employees.count()}"
        elements.append(Paragraph(meta_text, meta_style))
        elements.append(Spacer(1, 0.3*cm))

        # Стиль для тексту в комірках з переносом
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='DejaVuSans',
            fontSize=5,
            leading=6,
            wordWrap='CJK'
        )

        # Функція для обрізання тексту
        def truncate(text, max_len):
            return text[:max_len] + '...' if len(text) > max_len else text

        # Функція для створення Paragraph (для переносу слів)
        def make_paragraph(text):
            if not text:
                return ''
            return Paragraph(text.replace('\n', '<br/>'), cell_style)

        # Дані таблиці
        data = [t['headers']]

        # Мапінг статусів
        status_map = t['status_map']

        for idx, emp in enumerate(employees, 1):
            # Період роботи (короткий формат дат)
            periods = []
            for period in emp.employment_period.all():
                start = period.start_date.strftime('%d.%m.%y') if period.start_date else ''
                end = period.end_date.strftime('%d.%m.%y') if period.end_date else ''
                if start or end:
                    periods.append(f"{start}-{end}")
            period_text = '\n'.join(periods[:2]) if periods else ''  # Макс 2 періоди

            # Документи (скорочено)
            docs = []
            for doc in emp.documents.all():
                doc_text = doc.doc_type or ''
                if doc.valid_until:
                    doc_text += f"({doc.valid_until.strftime('%d.%m.%y')})"
                if doc_text:
                    docs.append(truncate(doc_text, 20))
            docs_text = '\n'.join(docs[:2]) if docs else ''  # Макс 2 документи

            # Дозволи (з переносом слів через Paragraph)
            permits = []
            for permit in emp.work_permits.all():
                permit_text = permit.doc_type or ''
                if permit.end_date:
                    permit_text += f" ({permit.end_date.strftime('%d.%m.%y')})"
                if permit_text:
                    permits.append(permit_text)
            permits_text = '<br/>'.join(permits[:3]) if permits else ''  # Макс 3 дозволи

            # Контракти (скорочено)
            contracts = []
            for contract in emp.contracts.all():
                if contract.contract_type:
                    contracts.append(truncate(contract.contract_type, 20))
            contracts_text = '\n'.join(contracts[:2]) if contracts else ''  # Макс 2 контракти

            # Контакти (з переносом слів)
            contacts = []
            for contact in emp.contacts.all():
                if contact.value:
                    contacts.append(contact.value)
            contacts_text = '<br/>'.join(contacts[:2]) if contacts else ''  # Макс 2 контакти

            row = [
                str(idx),
                truncate(emp.last_name or '', 12),
                truncate(emp.first_name or '', 10),
                str(emp.age) if emp.age else '',
                make_paragraph(emp.workplace or ''),  # Paragraph для переносу
                make_paragraph(status_map.get(emp.working_status, emp.working_status or '')),  # Paragraph для переносу
                emp.pesel or '',
                t['yes'] if emp.is_student else t['no'],
                period_text,
                docs_text,
                make_paragraph(permits_text),  # Paragraph для переносу
                contracts_text,
                make_paragraph(contacts_text)  # Paragraph для переносу
            ]
            data.append(row)
        
        # Створюємо таблицю з оптимізованими розмірами
        table = Table(data, colWidths=[
            0.5*cm,   # №
            1.9*cm,   # Прізвище
            1.5*cm,   # Ім'я
            0.5*cm,   # Вік
            1.7*cm,   # Місце роботи
            2.4*cm,   # Статус
            1.7*cm,   # PESEL
            1.0*cm,   # Студент
            2.2*cm,   # Період роботи
            2.1*cm,   # Документи
            3.7*cm,   # Дозвіл на роботу
            1.3*cm,   # Контракт
            2.2*cm    # Контакти
        ])

        # Стиль таблиці
        table.setStyle(TableStyle([
            # Заголовок
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 5.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('LEFTPADDING', (0, 0), (-1, 0), 2),
            ('RIGHTPADDING', (0, 0), (-1, 0), 2),

            # Дані
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 1), (-1, -1), 5),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 1), (-1, -1), 2),
            ('RIGHTPADDING', (0, 1), (-1, -1), 2),
            ('WORDWRAP', (0, 1), (-1, -1), True),

            # Сітка
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),

            # Чергування кольорів рядків
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        elements.append(table)
        
        # Генеруємо PDF
        pdf_doc.build(elements)
        
        logger.info("PDF generated successfully")
        
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"countdown": 60, "max_retries": 3})
def backup_postgres(self):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    filename = f"/backups/db_backup_{timestamp}.dump"

    cmd = [
        "pg_dump",
        "-h", os.getenv("POSTGRES_HOST", "db"),
        "-U", os.getenv("POSTGRES_USER"),
        "-d", os.getenv("POSTGRES_DB"),
        "-F", "c",      # custom format
        "-f", filename,
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD")

    subprocess.run(cmd, check=True, env=env)

    return f"Backup created: {filename}"


@shared_task
def cleanup_old_backups(days=14):
    import glob, time

    now = time.time()
    for f in glob.glob("/backups/db_backup_*.dump"):
        if os.stat(f).st_mtime < now - days * 86400:
            os.remove(f)
