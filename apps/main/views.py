import os

from functools import cached_property
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from django.template.loader import render_to_string
from django.views.generic import TemplateView, ListView
from django.db import transaction
from django.db.models import Case, When, IntegerField


from apps.main.models import Employee, History
from apps.users.models import InviteToken
from apps.notification.models import Notification
from apps.notification.utils import check_and_create_notifications
from datetime import timedelta
from .forms import EmployeeCompleteForm, ContactFormSet
from .filters import EmployeeMultiFilter
from .utils import set_change_user


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "main/dashboard.html"
    form_class = EmployeeCompleteForm
    success_url = reverse_lazy("main:dashboard")

    def get(self, request, *args, **kwargs):
        """Handle GET requests for dashboard and HTMX partials"""
        # HTMX partial requests
        if request.headers.get('HX-Request'):
            return self.handle_htmx_request(request)

        # Regular full page request
        return self.render_to_response(self.get_context_data())

    def handle_htmx_request(self, request):
        """Route HTMX requests to appropriate handlers"""
        target = request.headers.get('HX-Target', '')

        # Table refresh (filters, pagination, sorting)
        if target == 'employees-table-body':
            return self.render_employees_table(request)

        # Modal for create/edit employee
        elif target == 'modal-container':
            employee_id = request.GET.get('employee_id')

            if employee_id:
                # View or Edit mode
                if request.path.endswith('/'):  # employee detail
                    return self.render_employee_detail(request, employee_id)
                else:  # employee form
                    return self.render_employee_modal(request, mode='edit', employee_id=employee_id)
            else:
                # Create mode
                return self.render_employee_modal(request, mode='create')

        # Filter dropdown
        elif target == 'filter-dropdown':
            return self.render_filter_dropdown(request)

        # Default fallback
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        """Handle POST requests for employee create/update"""
        set_change_user(request.user)

        action = request.POST.get('action', '')
        employee_id = request.POST.get('employee_id')

        if action == 'create':
            return self.create_employee(request)
        elif action == 'update' and employee_id:
            return self.update_employee(request, employee_id)

        return self.get(request, *args, **kwargs)

    def create_employee(self, request):
        """Create new employee"""
        form = self.form_class(request.POST)
        contact_formset = ContactFormSet(request.POST, prefix="contacts")

        if form.is_valid() and contact_formset.is_valid():
            try:
                employee = form.save_to_models()
                contact_formset.instance = employee
                contact_formset.save()

                messages.success(request, "Співробітника успішно додано")

                # Return updated table with new employee highlighted
                context = self.get_employees_context(request)
                context['new_employee_id'] = employee.id

                response = render(request, 'main/partials/employees_table_body.html', context)
                response['HX-Trigger'] = 'employeeCreated, closeModal'
                return response

            except Exception as e:
                messages.error(request, f"Помилка: {str(e)}")
                return self.render_form_with_errors(request, form, contact_formset, 'create')

        # Return form with errors
        return self.render_form_with_errors(request, form, contact_formset, 'create')

    def update_employee(self, request, employee_id):
        """Update existing employee"""
        employee = get_object_or_404(Employee, id=employee_id)

        # Check lock
        lock_key = f"employee_edit_lock:{employee_id}"
        locked_by = cache.get(lock_key)

        if locked_by and locked_by != request.user.id:
            messages.warning(request, "Цей співробітник зараз редагується іншим користувачем")
            response = render(request, 'main/partials/error_message.html', {
                'message': 'Співробітник заблокований'
            })
            response['HX-Trigger'] = 'closeModal'
            return response

        form = self.form_class(request.POST)
        contact_formset = ContactFormSet(
            request.POST,
            prefix="contacts",
            instance=employee
        )

        if form.is_valid() and contact_formset.is_valid():
            try:
                employee = form.save_to_models(employee_id=employee_id)
                contact_formset.instance = employee
                contact_formset.save()

                # Unlock employee
                cache.delete(lock_key)

                messages.success(request, "Дані співробітника оновлено")

                # Return updated table with employee highlighted
                context = self.get_employees_context(request)
                context['updated_employee_id'] = employee_id

                response = render(request, 'main/partials/employees_table_body.html', context)
                response['HX-Trigger'] = 'employeeUpdated, closeModal'
                return response

            except Exception as e:
                messages.error(request, f"Помилка: {str(e)}")
                return self.render_form_with_errors(request, form, contact_formset, 'edit', employee_id)

        # Return form with errors
        return self.render_form_with_errors(request, form, contact_formset, 'edit', employee_id)

    def render_form_with_errors(self, request, form, contact_formset, mode, employee_id=None):
        """Render form with validation errors"""
        return render(request, 'main/partials/employee_modal.html', {
            'form': form,
            'contact_formset': contact_formset,
            'mode': mode,
            'employee_id': employee_id
        })

    def render_employees_table(self, request):
        """Render just the table body for HTMX updates"""
        context = self.get_employees_context(request)
        return render(request, 'main/partials/employees_table_body.html', context)

    def render_employee_modal(self, request, mode='create', employee_id=None):
        """Render employee form modal"""
        if mode == 'edit' and employee_id:
            # Check and set lock
            lock_key = f"employee_edit_lock:{employee_id}"
            locked_by = cache.get(lock_key)

            if locked_by and locked_by != request.user.id:
                return render(request, 'main/partials/error_message.html', {
                    'message': 'Цей співробітник зараз редагується іншим користувачем'
                })

            # Set lock
            cache.set(lock_key, request.user.id, timeout=300)

            employee = get_object_or_404(Employee, id=employee_id)

            # Prefetch related data
            employee = Employee.objects.prefetch_related(
                'employment_period',
                'documents',
                'work_permits',
                'card_submissions',
                'contracts',
                'sanepids',
                'contacts'
            ).get(id=employee_id)

            form = self.form_class(initial={
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "age": employee.age,
                "is_student": "true" if employee.is_student else "false",
                "pesel": employee.pesel,
                "pesel_urk": "true" if employee.pesel_urk else "false",
                "workplace": employee.workplace,
                "pit_2": "true" if employee.pit_2 else "false",
                "working_status": employee.working_status,
                "additional_information": employee.additional_information,
                "student_end_date": employee.student_end_date,
                # Add other fields as needed
            })
            contact_formset = ContactFormSet(instance=employee, prefix="contacts")
        else:
            form = self.form_class()
            contact_formset = ContactFormSet(prefix="contacts")
            employee_id = None

        return render(request, 'main/partials/employee_modal.html', {
            'form': form,
            'contact_formset': contact_formset,
            'mode': mode,
            'employee_id': employee_id
        })

    def render_employee_detail(self, request, employee_id):
        """Render employee detail modal"""
        # Prefetch related data
        employee = Employee.objects.prefetch_related(
            'employment_period',
            'documents',
            'work_permits',
            'card_submissions',
            'contracts',
            'sanepids',
            'contacts'
        ).get(id=employee_id)

        return render(request, 'main/partials/employee_detail.html', {
            'employee': employee,
        })

    def render_filter_dropdown(self, request):
        """Render filter dropdown"""
        filter_obj = EmployeeMultiFilter(request.GET, queryset=self.base_queryset)
        return render(request, 'main/partials/filter_dropdown.html', {
            'filter': filter_obj
        })

    @cached_property
    def base_queryset(self):
        """Base queryset with optimizations"""
        return (
            Employee.objects
            .base_select()
            .with_period_annotations()
            .annotate(
                status_priority=Case(
                    When(working_status='Zwolniony', then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )
        ).order_by('status_priority', '-id')

    def _parse_ordering(self, ordering):
        """Parse ordering parameter"""
        ordering_info = {
            'last_name': {'active': False, 'direction': None},
            'start_date': {'active': False, 'direction': None},
            'end_date': {'active': False, 'direction': None},
        }

        if not ordering:
            return ordering_info

        is_descending = ordering.startswith('-')
        field_name = ordering.lstrip('-')

        if field_name in ordering_info:
            ordering_info[field_name] = {
                'active': True,
                'direction': 'desc' if is_descending else 'asc'
            }

        return ordering_info

    def get_filtered_employees(self, request):
        """Get filtered employees with caching"""
        params = request.GET.copy()
        params.pop("page", None)
        cache_key = "filtered:" + params.urlencode()

        ids = cache.get(cache_key)
        if ids is None:
            filtered_qs = EmployeeMultiFilter(
                request.GET, queryset=self.base_queryset
            ).qs
            ids = list(filtered_qs.values_list("id", flat=True))
            cache.set(cache_key, ids, timeout=30)

        qs = self.base_queryset.filter(id__in=ids)

        # Apply ordering
        current_ordering = request.GET.get("ordering", "")
        if current_ordering:
            is_desc = current_ordering.startswith("-")
            raw_field = current_ordering.lstrip("-")

            ordering_map = {
                "last_name": "last_name",
                "start_date": "earliest_start_date",
                "end_date": "latest_end_date",
            }
            mapped = ordering_map.get(raw_field, raw_field)
            order_expr = ("-" if is_desc else "") + mapped
            qs = qs.order_by('status_priority', order_expr, '-id')
        else:
            qs = qs.order_by('status_priority', '-id')

        return qs

    def get_paginated_employees(self, request):
        """Get paginated employees"""
        qs = self.get_filtered_employees(request)

        paginator = Paginator(qs, 25)
        page_number = request.GET.get("page", 1)

        try:
            page_obj = paginator.get_page(page_number)
        except Exception:
            page_obj = paginator.get_page(1)

        # Prefetch related objects
        prefetched = page_obj.object_list.prefetch_related(
            "employment_period",
            "documents",
            "work_permits",
            "card_submissions",
            "contracts",
            "sanepids",
            "contacts",
        )

        page_obj.object_list = prefetched
        return page_obj

    def get_employees_context(self, request):
        """Get context for employees table"""
        paginated = self.get_paginated_employees(request)
        params = request.GET.copy()

        if "page" in params:
            params.pop("page")

        params_without_ordering = params.copy()
        if "ordering" in params_without_ordering:
            params_without_ordering.pop("ordering")

        current_ordering = request.GET.get("ordering", "")
        ordering_info = self._parse_ordering(current_ordering)

        if not hasattr(self, "filterset"):
            self.filterset = EmployeeMultiFilter(
                request.GET, queryset=self.base_queryset
            )

        count_key = "count:" + params.urlencode()
        total_count = cache.get(count_key)

        if total_count is None:
            total_count = self.filterset.qs.count()
            cache.set(count_key, total_count, 60 * 5)

        return {
            "employees": paginated,
            "params": params.urlencode(),
            "params_without_ordering": params_without_ordering.urlencode(),
            "current_ordering": current_ordering,
            "ordering_info": ordering_info,
            "total_count": total_count,
        }

    def get_context_data(self, **kwargs):
        """Get full page context"""
        context = super().get_context_data(**kwargs)

        # Add employees context
        context.update(self.get_employees_context(self.request))

        # Add forms
        context.update({
            "form": self.form_class(),
            "contact_formset": ContactFormSet(prefix="contacts"),
            "filter": EmployeeMultiFilter(
                self.request.GET,
                queryset=self.base_queryset
            ),
        })

        return context


@login_required
def invites_for_register(request):
    """Головна сторінка (захищена)"""
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            messages.error(request, _("Вкажіть пошту"))
            return redirect("main:invites")
        existing_invite = InviteToken.objects.filter(
            email=email,
        ).first()

        if existing_invite:
            messages.warning(request, _("Посилання на реєстрацію за цією поштою вже існує"))
            return redirect("main:invites")

        expires_at = timezone.now() + timedelta(days=7)
        invite = InviteToken.objects.create(email=email, expires_at=expires_at)
        if send_invitation_email(invite, request):
            messages.success(request, _("Запрошення успішно відправлено!"))
        else:
            messages.error(request, _("Помилка відправки запрошення"))

        return redirect("main:invites")

    invites = InviteToken.objects.all()
    return render(
        request,
        "main/invites.html",
        {
            "user": request.user,
            "invites": invites,
        },
    )


@login_required
def tasks_board(request):
    """Сторінка з дошкою завдань"""
    return render(request, 'main/tasks_board.html', {
        'user': request.user,
    })


@login_required
def expired_docs(request):
    """Сторінка з документами, термін дії яких закінчується"""
    notifications = Notification.objects.select_related("document", "work_permit").order_by('days_left')
    notifications_count = notifications.count()
    
    return render(request, 'main/expired_docs.html', {
        'user': request.user,
        'notifications': notifications,
        'notifications_count': notifications_count,
    })


def send_invitation_email(invite, request):
    try:
        registration_url = request.build_absolute_uri(
            reverse('accounts:register_page') + f'?invite={invite.token}'
        )

        context = {
            'email': invite.email,
            'registration_url': registration_url,
            'expires_at': invite.expires_at,
            'days_valid': 7,
        }

        subject = _("Посилання на реєстрацію Akorasp")
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [invite.email]

        text_content = _(
            "Вітаємо!\n\n"
            "Вас запросили зареєструватися на Akorasp.\n\n"
            "Посилання для реєстрації: {url}\n\n"
            "Це запрошення дійсне протягом {days} днів.\n\n"
            "З найкращими побажаннями,\n"
            "Команда Akorasp"
        ).format(url=registration_url, days=7)

        html_content = render_to_string("email/invitation_email.html", context)

        msg = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            to,
            headers={
                'X-Priority': '3',
                'X-MSMail-Priority': 'Normal',
                'Importance': 'Normal',
                'List-Unsubscribe': f'<mailto:{from_email}?subject=unsubscribe>',
                'Precedence': 'bulk',
            }
        )
        msg.attach_alternative(html_content, "text/html")

        attach_logo_to_email(msg)

        msg.send()
        return True

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send invitation email to {invite.email}: {str(e)}")
        return False


def attach_logo_to_email(msg):
    logo_path = os.path.join(settings.BASE_DIR, "static/images/logo.png")

    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<logo>")
                logo.add_header("Content-Disposition", "inline", filename="logo.png")
                msg.attach(logo)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to attach logo to email: {str(e)}")


@login_required
def lock_employee(request):
    """Встановлює блокування на співробітника при відкритті модального вікна"""
    import logging
    import json
    logger = logging.getLogger(__name__)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            employee_id = data.get("employee_id")
            logger.info(
                f"Lock request: employee_id={employee_id}, user={request.user.id}")

            if employee_id:
                lock_key = f"employee_edit_lock:{employee_id}"

                # Перевіряємо поточний стан блокування
                locked_by = cache.get(lock_key)
                logger.info(f"Current lock status: locked_by={locked_by}")

                # Якщо блокування вже встановлене НАМИ - оновлюємо час
                if locked_by == request.user.id:
                    cache.set(lock_key, request.user.id, timeout=300)
                    logger.info(f"Lock refreshed for employee {employee_id}")
                    return HttpResponse(json.dumps({"success": True}), content_type="application/json", status=200)

                # Якщо блокування встановлене КИМОСЬ ІНШИМ - відмовляємо
                if locked_by and locked_by != request.user.id:
                    logger.warning(
                        f"Employee {employee_id} is locked by user {locked_by}")
                    return HttpResponse(
                        json.dumps(
                            {"error": "Цей співробітник зараз редагується іншим користувачем"}),
                        content_type="application/json",
                        status=423
                    )

                # ✅ АТОМАРНА ОПЕРАЦІЯ: встановлюємо блокування тільки якщо його немає
                was_added = cache.add(lock_key, request.user.id, timeout=300)

                if was_added:
                    logger.info(f"Lock set for employee {employee_id}")
                    return HttpResponse(json.dumps({"success": True}), content_type="application/json", status=200)
                else:
                    # Хтось встиг встановити блокування між нашою перевіркою і спробою встановити
                    locked_by = cache.get(lock_key)
                    logger.warning(
                        f"Race condition: employee {employee_id} was locked by user {locked_by}")
                    return HttpResponse(
                        json.dumps(
                            {"error": "Цей співробітник зараз редагується іншим користувачем"}),
                        content_type="application/json",
                        status=423
                    )
        except Exception as e:
            logger.error(f"Error in lock_employee: {e}")
            return HttpResponse(json.dumps({"error": str(e)}), content_type="application/json", status=500)

    return HttpResponse(status=400)


@login_required
def unlock_employee(request):
    """Знімає блокування з співробітника при закритті модального вікна"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            employee_id = data.get("employee_id")
            logger.info(f"Unlock request: employee_id={employee_id}, user={request.user.id}")
            
            if employee_id:
                lock_key = f"employee_edit_lock:{employee_id}"
                locked_by = cache.get(lock_key)
                logger.info(f"Lock status: locked_by={locked_by}")
                
                # Знімаємо блокування тільки якщо воно встановлене поточним користувачем
                if locked_by and locked_by == request.user.id:
                    cache.delete(lock_key)
                    logger.info(f"Lock removed for employee {employee_id}")
                    return HttpResponse(json.dumps({"success": True}), content_type="application/json", status=200)
                elif not locked_by:
                    # Блокування вже знято або не існувало
                    logger.info(f"No lock found for employee {employee_id}")
                    return HttpResponse(json.dumps({"success": True}), content_type="application/json", status=200)
                else:
                    # Блокування належить іншому користувачу - це нормально, просто ігноруємо
                    logger.warning(f"Lock owned by different user: {locked_by} != {request.user.id}")
                    return HttpResponse(json.dumps({"success": False, "message": "Lock owned by another user"}), content_type="application/json", status=200)
        except Exception as e:
            logger.error(f"Error in unlock_employee: {e}")
            return HttpResponse(json.dumps({"error": str(e)}), content_type="application/json", status=500)
    
    logger.error(f"Bad request: method={request.method}")
    return HttpResponse(status=400)


@login_required
def export_employees_pdf(request):
    """Експорт співробітників у PDF через Celery"""
    from apps.main.tasks import generate_employees_pdf_task
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting PDF export via Celery")

    # Додаємо мову до параметрів
    params = dict(request.GET)
    params['language'] = request.LANGUAGE_CODE

    # Запускаємо задачу в Celery
    task = generate_employees_pdf_task.delay(params)
    
    # Чекаємо на результат (з таймаутом 120 секунд)
    try:
        pdf_content = task.get(timeout=120)
        
        logger.info("PDF generated successfully via Celery")
        
        # Повертаємо PDF як відповідь
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="employees_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        messages.error(request, _('Помилка генерації PDF. Спробуйте пізніше.'))
        return redirect('main:dashboard')


class HistoryListView(ListView):
    model = History
    template_name = "main/history_list.html"
    context_object_name = "history"
    paginate_by = 10

    def get_queryset(self):
        qs = History.objects.select_related("changed_by", "content_type")

        user_id = self.request.GET.get("user")

        if user_id:
            qs = qs.filter(changed_by_id=user_id)

        return qs.order_by('-changed_at')

    def get_context_data(self, **kwargs):
        from apps.users.models import User
        
        ctx = super().get_context_data(**kwargs)

        ctx["users"] = User.objects.filter(
            id__in=History.objects.values_list("changed_by", flat=True).distinct()
        ).order_by('first_name', 'last_name')
        
        return ctx