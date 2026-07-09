"""
MUDRA - Campus Fintech Application
models.py — Database models for BankUser, Transaction, LoanRequest
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM USER MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class BankUserManager(BaseUserManager):
    """
    Custom manager for BankUser.
    Uses roll_number as the unique identifier instead of username/email.
    """

    def create_user(self, roll_number, password=None, **extra_fields):
        if not roll_number:
            raise ValueError('The Roll Number must be set')
        user = self.model(roll_number=roll_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, roll_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(roll_number, password, **extra_fields)


# ─────────────────────────────────────────────────────────────────────────────
# BANK USER MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BankUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for MUDRA.
    - roll_number is the primary login identifier (replaces username)
    - balance holds the current wallet balance
    - face_signature stores a mock biometric hash for FaceID simulation
    """

    roll_number     = models.CharField(max_length=20, unique=True)
    name            = models.CharField(max_length=150)
    balance         = models.DecimalField(max_digits=12, decimal_places=2, default=10000.00)
    face_signature  = models.TextField(blank=True, null=True,
                                       help_text="Mock biometric hash for FaceID simulation")

    is_active  = models.BooleanField(default=False)
    is_staff   = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = BankUserManager()

    USERNAME_FIELD  = 'roll_number'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name      = 'Bank User'
        verbose_name_plural = 'Bank Users'

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION MODEL
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(models.Model):
    """
    Logs every monetary movement in the system.
    - sender / receiver both reference BankUser
    - transaction_type distinguishes between a regular transfer and a bill-split payout
    """

    CATEGORY_CHOICES = [
        ('Mess Fee', 'Mess Fee'),
        ('Canteen',  'Canteen'),
        ('Books',    'Books'),
        ('Hostel',   'Hostel'),
        ('General',  'General'),
    ]

    TRANSACTION_TYPE_CHOICES = [
        ('Transfer',   'Transfer'),
        ('Bill Split', 'Bill Split'),
        ('Loan',       'Loan'),
    ]

    sender           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_transactions',
        on_delete=models.CASCADE
    )
    receiver         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_transactions',
        on_delete=models.CASCADE
    )
    amount           = models.DecimalField(max_digits=12, decimal_places=2)
    category         = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='Transfer')
    note             = models.CharField(max_length=255, blank=True, default='')
    timestamp        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f"{self.transaction_type} | {self.sender.roll_number} → "
            f"{self.receiver.roll_number} : ₹{self.amount}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LOAN REQUEST MODEL
# ─────────────────────────────────────────────────────────────────────────────

class LoanRequest(models.Model):
    """
    Stores student loan applications.
    - status moves from Pending → Approved/Rejected by a superuser
    - On Approved, the user's balance is credited by the loan amount
    """

    STATUS_CHOICES = [
        ('Pending',  'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='loans',
        on_delete=models.CASCADE
    )
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    purpose    = models.CharField(max_length=255)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan #{self.id} — {self.user.roll_number} — ₹{self.amount} ({self.status})"
