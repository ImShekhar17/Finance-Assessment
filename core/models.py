from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('ANALYST', 'Analyst'),
        ('VIEWER', 'Viewer'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='VIEWER')
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    application_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    membership_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def generate_application_id(self):
        import uuid
        return f"APP-{uuid.uuid4().hex[:8].upper()}"

    def __str__(self):
        return f"{self.username} ({self.role})"

class FinancialRecord(models.Model):
    TYPE_CHOICES = (
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def delete(self, **kwargs):
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.type}: {self.amount} - {self.category}"
