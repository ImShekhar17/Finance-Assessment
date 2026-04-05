from django.contrib import admin
from .models import User, FinancialRecord

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'application_id', 'membership_id')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'application_id', 'membership_id')

@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'type', 'category', 'date', 'deleted_at')
    list_filter = ('type', 'category', 'date', 'user')
    search_fields = ('description', 'category')
    readonly_fields = ('deleted_at',)
