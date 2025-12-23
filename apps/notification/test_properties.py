"""
Property-based tests for document expiry notification system.
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase

from apps.main.models import Employee, Document, WorkPermit
from apps.notification.models import Notification
from apps.notification.utils import check_and_create_notifications


# Custom strategies for generating test data
@st.composite
def date_in_range(draw, start_offset_days=0, end_offset_days=60):
    """Generate a date within a specific range from today."""
    today = date.today()
    offset = draw(st.integers(min_value=start_offset_days, max_value=end_offset_days))
    return today + timedelta(days=offset)


@st.composite
def date_out_of_range(draw):
    """Generate a date outside the 2-month range (past or far future)."""
    today = date.today()
    target_date = today + relativedelta(months=2)
    choice = draw(st.booleans())
    if choice:
        # Past date
        offset = draw(st.integers(min_value=-365, max_value=-1))
    else:
        # Far future (more than 2 months + 1 day)
        days_to_target = (target_date - today).days
        offset = draw(st.integers(min_value=days_to_target + 1, max_value=365))
    return today + timedelta(days=offset)


@st.composite
def employee_with_expiring_documents(draw):
    """Generate an employee with documents expiring within 2 months."""
    employee = Employee.objects.create(
        first_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        last_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        age=draw(st.integers(min_value=18, max_value=70) | st.none())
    )
    
    # Generate 0-3 documents with expiring dates
    num_docs = draw(st.integers(min_value=0, max_value=3))
    for _ in range(num_docs):
        Document.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            number=draw(st.text(min_size=1, max_size=50) | st.none()),
            valid_until=draw(date_in_range())
        )
    
    # Generate 0-2 work permits with expiring dates
    num_permits = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_permits):
        WorkPermit.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            end_date=draw(date_in_range())
        )
    
    return employee


@st.composite
def employee_with_out_of_range_documents(draw):
    """Generate an employee with documents expiring outside the 2-month range."""
    employee = Employee.objects.create(
        first_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        last_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        age=draw(st.integers(min_value=18, max_value=70) | st.none())
    )
    
    # Generate 1-3 documents with out-of-range dates
    num_docs = draw(st.integers(min_value=1, max_value=3))
    for _ in range(num_docs):
        Document.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            number=draw(st.text(min_size=1, max_size=50) | st.none()),
            valid_until=draw(date_out_of_range())
        )
    
    # Generate 0-2 work permits with out-of-range dates
    num_permits = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_permits):
        WorkPermit.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            end_date=draw(date_out_of_range())
        )
    
    return employee


@st.composite
def employee_with_null_dates(draw):
    """Generate an employee with documents that have null expiration dates."""
    employee = Employee.objects.create(
        first_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        last_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        age=draw(st.integers(min_value=18, max_value=70) | st.none())
    )
    
    # Generate 1-3 documents with null dates
    num_docs = draw(st.integers(min_value=1, max_value=3))
    for _ in range(num_docs):
        Document.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            number=draw(st.text(min_size=1, max_size=50) | st.none()),
            valid_until=None
        )
    
    # Generate 0-2 work permits with null dates
    num_permits = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_permits):
        WorkPermit.objects.create(
            employee=employee,
            doc_type=draw(st.text(min_size=1, max_size=50) | st.none()),
            end_date=None
        )
    
    return employee


class NotificationPropertyTests(TestCase):
    """Property-based tests for notification creation."""
    
    def tearDown(self):
        """Clean up after each test."""
        Notification.objects.all().delete()
        Document.objects.all().delete()
        WorkPermit.objects.all().delete()
        Employee.objects.all().delete()
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_expiring_documents())
    def test_property_1_notifications_created_for_expiring_documents(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 1: Notifications created for expiring documents
        Validates: Requirements 1.2, 1.5, 2.2, 2.4
        
        For any employee with documents or work permits that have expiration dates 
        within the range [today, today + 2 months], calling the check function should 
        create notifications for all such documents and permits that don't already have notifications.
        """
        today = date.today()
        target_date = today + relativedelta(months=2)
        
        # Count expected notifications
        expected_doc_count = employee.documents.filter(
            valid_until__isnull=False,
            valid_until__gte=today,
            valid_until__lte=target_date
        ).count()
        
        expected_permit_count = employee.work_permits.filter(
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=target_date
        ).count()
        
        expected_total = expected_doc_count + expected_permit_count
        
        # Call the function
        check_and_create_notifications(employee)
        
        # Verify notifications were created
        actual_count = Notification.objects.filter(employee=employee).count()
        self.assertEqual(actual_count, expected_total,
                        f"Expected {expected_total} notifications, got {actual_count}")
        
        # Verify each document notification
        for doc in employee.documents.filter(
            valid_until__isnull=False,
            valid_until__gte=today,
            valid_until__lte=target_date
        ):
            self.assertTrue(
                Notification.objects.filter(document=doc, employee=employee).exists(),
                f"Notification not created for document {doc.id}"
            )
        
        # Verify each work permit notification
        for permit in employee.work_permits.filter(
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=target_date
        ):
            self.assertTrue(
                Notification.objects.filter(work_permit=permit, employee=employee).exists(),
                f"Notification not created for work permit {permit.id}"
            )
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_expiring_documents())
    def test_property_2_days_left_calculation_accuracy(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 2: Days left calculation accuracy
        Validates: Requirements 1.3
        
        For any created notification, the days_left value should equal the number of days 
        between the current date and the document's expiration date.
        """
        today = date.today()
        
        # Call the function
        check_and_create_notifications(employee)
        
        # Check all document notifications
        for notification in Notification.objects.filter(
            employee=employee,
            notification_type="document"
        ):
            expected_days = (notification.document.valid_until - today).days
            self.assertEqual(
                notification.days_left,
                expected_days,
                f"Days left mismatch: expected {expected_days}, got {notification.days_left}"
            )
        
        # Check all work permit notifications
        for notification in Notification.objects.filter(
            employee=employee,
            notification_type="work_permit"
        ):
            expected_days = (notification.work_permit.end_date - today).days
            self.assertEqual(
                notification.days_left,
                expected_days,
                f"Days left mismatch: expected {expected_days}, got {notification.days_left}"
            )
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_expiring_documents())
    def test_property_3_idempotency_of_notification_creation(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 3: Idempotency of notification creation
        Validates: Requirements 3.1, 3.2, 3.3
        
        For any employee, calling the check function multiple times should not create 
        duplicate notifications - the second call should not create any new notifications 
        if the documents haven't changed.
        """
        # First call
        check_and_create_notifications(employee)
        count_after_first = Notification.objects.filter(employee=employee).count()
        
        # Second call
        check_and_create_notifications(employee)
        count_after_second = Notification.objects.filter(employee=employee).count()
        
        # Third call for good measure
        check_and_create_notifications(employee)
        count_after_third = Notification.objects.filter(employee=employee).count()
        
        self.assertEqual(
            count_after_first,
            count_after_second,
            "Second call created duplicate notifications"
        )
        self.assertEqual(
            count_after_second,
            count_after_third,
            "Third call created duplicate notifications"
        )
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_expiring_documents())
    def test_property_4_message_format_correctness(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 4: Message format correctness
        Validates: Requirements 4.1, 4.2, 4.3, 4.4
        
        For any created notification, the message should contain the document type, 
        the number of days left, and the expiration date in the correct format, 
        with "Невідомий" used for missing doc_type and "Не вказано" used for missing document number.
        """
        # Call the function
        check_and_create_notifications(employee)
        
        # Check document notifications
        for notification in Notification.objects.filter(
            employee=employee,
            notification_type="document"
        ):
            doc = notification.document
            doc_type = doc.doc_type or "Невідомий"
            doc_number = doc.number or "Не вказано"
            
            # Verify message contains expected components
            self.assertIn(doc_type, notification.message,
                         f"Message missing doc_type: {notification.message}")
            self.assertIn(doc_number, notification.message,
                         f"Message missing doc_number: {notification.message}")
            self.assertIn(str(notification.days_left), notification.message,
                         f"Message missing days_left: {notification.message}")
            self.assertIn(str(doc.valid_until), notification.message,
                         f"Message missing valid_until: {notification.message}")
        
        # Check work permit notifications
        for notification in Notification.objects.filter(
            employee=employee,
            notification_type="work_permit"
        ):
            permit = notification.work_permit
            doc_type = permit.doc_type or "Невідомий"
            
            # Verify message contains expected components
            self.assertIn(doc_type, notification.message,
                         f"Message missing doc_type: {notification.message}")
            self.assertIn(str(notification.days_left), notification.message,
                         f"Message missing days_left: {notification.message}")
            self.assertIn(str(permit.end_date), notification.message,
                         f"Message missing end_date: {notification.message}")
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_out_of_range_documents())
    def test_property_5_no_notifications_for_out_of_range_dates(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 5: No notifications for out-of-range dates
        Validates: Requirements 5.3
        
        For any employee with documents that have expiration dates outside the range 
        [today, today + 2 months] (either in the past or more than 2 months in the future), 
        calling the check function should not create notifications for those documents.
        """
        # Call the function
        check_and_create_notifications(employee)
        
        # Verify no notifications were created
        notification_count = Notification.objects.filter(employee=employee).count()
        self.assertEqual(
            notification_count,
            0,
            f"Expected 0 notifications for out-of-range documents, got {notification_count}"
        )
    
    @settings(max_examples=100, deadline=None)
    @given(employee_with_null_dates())
    def test_property_6_null_date_handling(self, employee):
        """
        Feature: document-expiry-check-on-employee-save, Property 6: Null date handling
        Validates: Requirements 5.1, 5.2
        
        For any employee with documents or work permits that have null expiration dates, 
        calling the check function should not raise errors and should skip those documents.
        """
        # This should not raise any exceptions
        try:
            check_and_create_notifications(employee)
        except Exception as e:
            self.fail(f"Function raised exception with null dates: {e}")
        
        # Verify no notifications were created (since all dates are null)
        notification_count = Notification.objects.filter(employee=employee).count()
        self.assertEqual(
            notification_count,
            0,
            f"Expected 0 notifications for null dates, got {notification_count}"
        )
