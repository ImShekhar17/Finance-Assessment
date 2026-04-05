from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, FinancialRecord
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
import json

class FinanceAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin_test', email='admin@test.com', password='password', role='ADMIN'
        )
        self.analyst_user = User.objects.create_user(
            username='analyst_test', email='analyst@test.com', password='password', role='ANALYST'
        )
        self.viewer_user = User.objects.create_user(
            username='viewer_test', email='viewer@test.com', password='password', role='VIEWER'
        )

    def get_token(self, email, password):
        # Note: Our login uses email as primary identifier in this helper
        response = self.client.post('/api/auth/login/', {'email': email, 'password': password})
        return response.data['access']

    def test_signup_and_verify_otp(self):
        # 1. Signup
        signup_data = {
            "username": "new_user",
            "email": "new@test.com",
            "password": "password123",
            "mobile_number": "0000000000",
            "name": "New User",
            "role": "VIEWER"
        }
        res = self.client.post('/api/auth/signup/', signup_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # 2. Verify OTP (We mock the session OTP since it's hard to get from terminal in tests)
        session = self.client.session
        session['otp'] = '123456'
        from django.utils import timezone
        from datetime import timedelta
        session['otp_expires_at'] = (timezone.now() + timedelta(minutes=5)).isoformat()
        session.save()
        
        verify_data = {"email": "new@test.com", "otp": "123456"}
        res = self.client.post('/api/auth/verify-otp/', verify_data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("application_id", res.data)
        
        # 3. Check if user is active
        user = User.objects.get(email="new@test.com")
        self.assertTrue(user.is_active)

    def test_admin_can_view_all_records(self):
        FinancialRecord.objects.create(user=self.analyst_user, amount=100, type='INCOME', category='Test', date='2024-01-01')
        token = self.get_token('admin@test.com', 'password')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/records/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_viewer_cannot_create_record(self):
        token = self.get_token('viewer@test.com', 'password')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/api/records/', {
            'amount': 100, 'type': 'INCOME', 'category': 'Test', 'date': '2024-01-01'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_delete(self):
        record = FinancialRecord.objects.create(user=self.analyst_user, amount=100, type='INCOME', category='Test', date='2024-01-01')
        token = self.get_token('analyst@test.com', 'password')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.delete(f'/api/records/{record.id}/')
        
        # Check if it's still in DB but has deleted_at set
        record.refresh_from_db()
        self.assertIsNotNone(record.deleted_at)
        
        # Check if it's excluded from list
        response = self.client.get('/api/records/')
        self.assertEqual(response.data['count'], 0)

    def test_password_reset_flow(self):
        # 1. Request Reset
        res = self.client.post('/api/auth/password-reset/', {"email": "analyst@test.com"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # 2. Confirm Reset (Mock token and uid)
        user = self.analyst_user
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        res = self.client.post(f'/api/auth/password-reset-confirm/?uid={uid}&token={token}', {"new_password": "new_password123"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # 3. Try to login with new password
        res = self.client.post('/api/auth/login/', {"email": "analyst@test.com", "password": "new_password123"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_dashboard_summary(self):
        FinancialRecord.objects.create(user=self.analyst_user, amount=500, type='INCOME', category='Consulting', date='2024-01-01')
        token = self.get_token('admin@test.com', 'password')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res = self.client.get('/api/dashboard/summary/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_income'], 500.0)
