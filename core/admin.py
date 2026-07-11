"""
MUDRA - Campus Fintech Application
admin.py — Django admin panel configuration
"""

from django.contrib import admin
from .models import BankUser, Transaction, LoanRequest, Beneficiary, SupportTicket

# ─────────────────────────────────────────────────────────────────────────────
# BANK USER ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(BankUser)
class BankUserAdmin(admin.ModelAdmin):
    # CHANGED: 'balance' updated to 'wallet_balance'
    list_display    = ('roll_number', 'name', 'wallet_balance', 'is_active', 'is_staff', 'date_joined')
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
            # CHANGED: 'balance' updated to 'wallet_balance'
            loan.user.wallet_balance += loan.amount
            loan.user.save(update_fields=['wallet_balance'])
            count += 1
        self.message_user(request, f"{count} loan(s) approved and balances credited.")
    approve_loans.short_description = "✅ Approve selected loans"

    def reject_loans(self, request, queryset):
        updated = queryset.filter(status='Pending').update(status='Rejected')
        self.message_user(request, f"{updated} loan(s) rejected.")
    reject_loans.short_description = "❌ Reject selected loans"


# ─────────────────────────────────────────────────────────────────────────────
# BENEFICIARY ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_id', 'added_on')
    search_fields = ('name', 'student_id')


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKET ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display   = ('ticket_id', 'user', 'subject', 'category', 'status', 'priority', 'created_at')
    list_filter    = ('status', 'priority', 'category', 'created_at')
    search_fields  = ('ticket_id', 'user__roll_number', 'subject', 'description')
    ordering       = ('-created_at',)
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    
    actions = ['mark_resolved', 'mark_in_progress']

    def mark_resolved(self, request, queryset):
        updated = queryset.update(status='Resolved')
        self.message_user(request, f"{updated} ticket(s) marked as Resolved.")
    mark_resolved.short_description = "✅ Mark selected tickets as Resolved"

    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='In Progress')
        self.message_user(request, f"{updated} ticket(s) marked as In Progress.")
    mark_in_progress.short_description = "⏳ Mark selected tickets as In Progress"