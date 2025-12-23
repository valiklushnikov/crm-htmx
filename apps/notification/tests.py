"""Unit tests for notification utility functions."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.test import TestCase

from apps.main.models import Employee, Document, WorkPermit
from apps.notification.models import Notification
from apps.notification.utils import check_and_create_notifications


class NotificationUtilityTests(TestCase):
    """Unit tests for check_and_create_notifications function."""

    def setUp(self):
        """Set up test data."""
        self.employee = Employee.objects.create(
            first_name="Test",
            last_name="Employee",
            age=30
        )

    def tearDown(self):
        """Clean up after each test."""
        Notification.objects.all().delete()
        Document.objects.all().delete()
        WorkPermit.objects.all().delete()
        Employee.objects.all().delete()

    def test_basic_notification_creation_with_document_expiring_in_30_days(self):
        """Test creating notification for document expiring in 30 days."""
        expiry_date = date.today() + timedelta(days=30)
        document = Document.objects.create(
            employee=self.employee,
            doc_type="Passport",
            number="AB123456",
            valid_until=expiry_date
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 1)

        notification = notifications.first()
        self.assertEqual(notification.notification_type, "document")
        self.assertEqual(notification.document, document)
        self.assertEqual(notification.days_left, 30)
        self.assertIn("Passport", notification.message)
        self.assertIn("AB123456", notification.message)
        self.assertIn("30", notification.message)

    def test_handling_documents_without_expiration_dates(self):
        """Test that documents without expiration dates are skipped."""
        Document.objects.create(
            employee=self.employee,
            doc_type="ID Card",
            number="ID123",
            valid_until=None
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 0)

    def test_handling_missing_doc_type_and_number(self):
        """Test default values for missing doc_type and number."""
        expiry_date = date.today() + timedelta(days=15)
        Document.objects.create(
            employee=self.employee,
            doc_type=None,
            number=None,
            valid_until=expiry_date
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 1)

        notification = notifications.first()
        self.assertIn("Невідомий", notification.message)
        self.assertIn("Не вказано", notification.message)

    def test_no_notifications_for_documents_outside_2_month_range(self):
        """Test that documents outside 2-month range don't create notifications."""
        today = date.today()
        target_date = today + relativedelta(months=2)
        days_to_target = (target_date - today).days

        # Document expiring too far in the future
        Document.objects.create(
            employee=self.employee,
            doc_type="Future Doc",
            number="FUT001",
            valid_until=today + timedelta(days=days_to_target + 1)
        )

        # Document already expired
        Document.objects.create(
            employee=self.employee,
            doc_type="Past Doc",
            number="PST001",
            valid_until=today - timedelta(days=1)
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 0)

    def test_work_permit_notification_creation(self):
        """Test creating notification for work permit."""
        expiry_date = date.today() + timedelta(days=45)
        work_permit = WorkPermit.objects.create(
            employee=self.employee,
            doc_type="Work Permit Type A",
            end_date=expiry_date
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 1)

        notification = notifications.first()
        self.assertEqual(notification.notification_type, "work_permit")
        self.assertEqual(notification.work_permit, work_permit)
        self.assertEqual(notification.days_left, 45)
        self.assertIn("Work Permit Type A", notification.message)

    def test_multiple_documents_and_permits(self):
        """Test handling multiple documents and work permits."""
        # Create 2 documents expiring within range
        Document.objects.create(
            employee=self.employee,
            doc_type="Doc1",
            number="D1",
            valid_until=date.today() + timedelta(days=10)
        )
        Document.objects.create(
            employee=self.employee,
            doc_type="Doc2",
            number="D2",
            valid_until=date.today() + timedelta(days=20)
        )

        # Create 1 work permit expiring within range
        WorkPermit.objects.create(
            employee=self.employee,
            doc_type="Permit1",
            end_date=date.today() + timedelta(days=30)
        )

        check_and_create_notifications(self.employee)

        notifications = Notification.objects.filter(employee=self.employee)
        self.assertEqual(notifications.count(), 3)

        doc_notifications = notifications.filter(notification_type="document")
        self.assertEqual(doc_notifications.count(), 2)

        permit_notifications = notifications.filter(notification_type="work_permit")
        self.assertEqual(permit_notifications.count(), 1)
