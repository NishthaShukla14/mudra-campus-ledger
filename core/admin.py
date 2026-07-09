"""
MUDRA - Campus Fintech Application
admin.py — Django admin panel configuration
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BankUser, Transaction, LoanRequest


# ─────────────────────────────────────────────────────────────────────────────
# BANK USER ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(BankUser)
class BankUserAdmin(admin.ModelAdmin):
    list_display    = ('roll_number', 'name', 'balance', 'is_active', 'is_staff', 'date_joined')
    list_filter     = ('is_active', 'is_staff')
    search_fields   = ('roll_number', 'name')
    ordering        = ('roll_number',)
    readonly_fields = ('date_joined',)

    # Quick toggle for activating student accounts
    actions = ['activate_users', 'deactivate_users']

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} account(s) activated.")
    activate_users.short_description = "✅ Activate selected accounts"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} account(s) deactivated.")
    deactivate_users.short_description = "🚫 Deactivate selected accounts"


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display   = ('id', 'transaction_type', 'sender', 'receiver', 'amount', 'category', 'timestamp')
    list_filter    = ('transaction_type', 'category', 'timestamp')
    search_fields  = ('sender__roll_number', 'receiver__roll_number', 'category', 'note')
    ordering       = ('-timestamp',)
    readonly_fields = ('timestamp',)


# ─────────────────────────────────────────────────────────────────────────────
# LOAN REQUEST ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display   = ('id', 'user', 'amount', 'purpose', 'status', 'created_at')
    list_filter    = ('status', 'created_at')
    search_fields  = ('user__roll_number', 'user__name', 'purpose')
    ordering       = ('-created_at',)
    readonly_fields = ('created_at',)

    # Quick approve/reject directly from the list view
    actions = ['approve_loans', 'reject_loans']

    def approve_loans(self, request, queryset):
        pending = queryset.filter(status='Pending')
        count = 0
        for loan in pending:
            loan.status = 'Approved'
            loan.save(update_fields=['status'])
            # Credit balance
            loan.user.balance += loan.amount
            loan.user.save(update_fields=['balance'])
            count += 1
        self.message_user(request, f"{count} loan(s) approved and balances credited.")
    approve_loans.short_description = "✅ Approve selected loans"

    def reject_loans(self, request, queryset):
        updated = queryset.filter(status='Pending').update(status='Rejected')
        self.message_user(request, f"{updated} loan(s) rejected.")
    reject_loans.short_description = "❌ Reject selected loans"
