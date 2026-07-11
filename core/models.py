from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
from django.core.validators import RegexValidator

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
    - roll_number is the primary login identifier (Strictly 13 digits starting with 240122)
    - wallet_balance holds the current money
    """
    roll_validator = RegexValidator(
        regex=r'^240122\d{7}$', 
        message='Enter your University Roll No. starting with 240122 (Must be exactly 13 digits).'
    )
    
    roll_number = models.CharField(max_length=13, unique=True, validators=[roll_validator])
    name = models.CharField(max_length=150)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=5000.00)
    
    is_active = models.BooleanField(default=True) # Changed to True so users can actually log in
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    face_signature = models.TextField(blank=True, null=True)

    objects = BankUserManager()

    USERNAME_FIELD = 'roll_number'
    REQUIRED_FIELDS = ['name']

    @property
    def card_number(self):
        import hashlib
        hash_val = int(hashlib.md5(self.roll_number.encode()).hexdigest(), 16)
        num = str(hash_val).zfill(16)[:16]
        return f"{num[:4]} {num[4:8]} {num[8:12]} {num[12:16]}"

    class Meta:
        verbose_name = 'Bank User'
        verbose_name_plural = 'Bank Users'

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


# ─────────────────────────────────────────────────────────────────────────────
# BENEFICIARY MODEL
# ─────────────────────────────────────────────────────────────────────────────

class Beneficiary(models.Model):
    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION MODEL
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(models.Model):
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

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_transactions',
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_transactions',
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='Transfer')
    note = models.CharField(max_length=255, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} | {self.sender.roll_number} → {self.receiver.roll_number} : ₹{self.amount}"


# ─────────────────────────────────────────────────────────────────────────────
# LOAN REQUEST MODEL
# ─────────────────────────────────────────────────────────────────────────────

class LoanRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending',  'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='loans',
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan #{self.id} — {self.user.roll_number} — ₹{self.amount} ({self.status})"


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT REQUEST MODEL
# ─────────────────────────────────────────────────────────────────────────────

class PaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Declined', 'Declined'),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_payment_requests',
        on_delete=models.CASCADE
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_payment_requests',
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Req #{self.id} — {self.requester.roll_number} to {self.payer.roll_number} — ₹{self.amount} ({self.status})"


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKET MODEL
# ─────────────────────────────────────────────────────────────────────────────

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    CATEGORY_CHOICES = [
        ('Card Issue', 'Card Issue'),
        ('Fraud/Dispute', 'Fraud/Dispute'),
        ('Failed Transaction', 'Failed Transaction'),
        ('Loan Query', 'Loan Query'),
        ('Account Management', 'Account Management'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='support_tickets',
        on_delete=models.CASCADE
    )
    ticket_id = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_id} - {self.subject} ({self.status})"