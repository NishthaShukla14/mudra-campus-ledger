"""
MUDRA - Campus Fintech Application
views.py — All view logic: dashboard, AJAX APIs, FaceID, QR code
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import BankUser, Transaction, LoanRequest
from .forms import BankUserCreationForm, TransferForm
from decimal import Decimal

import json
import csv
import datetime
import hashlib


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: get CSRF-safe JSON error response
# ─────────────────────────────────────────────────────────────────────────────

def _json_error(message, status=400):
    return JsonResponse({'success': False, 'message': message}, status=status)


def _json_ok(data: dict):
    return JsonResponse({'success': True, **data})


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC PAGES
# ─────────────────────────────────────────────────────────────────────────────

def home(request):
    """Landing page — redirects authenticated users straight to dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def signup_view(request):
    """
    Registration page.
    Newly created accounts are inactive (is_active=False) until an admin
    approves them via the Django admin panel.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = BankUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False   # Requires admin activation
            user.save()
            messages.success(
                request,
                "Registration successful! Please wait for an admin to activate your account."
            )
            return redirect('login')
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)
    else:
        form = BankUserCreationForm()

    return render(request, 'core/signup.html', {'form': form})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Main dashboard view.
    Fetches live balance, transaction history, chart data, and loan info
    from the database and passes them to the template.
    """
    user = request.user

    # ── Transaction Data ──────────────────────────────────────────────────────
    sent_transactions     = Transaction.objects.filter(sender=user).order_by('-timestamp')
    received_transactions = Transaction.objects.filter(receiver=user).order_by('-timestamp')

    total_sent     = sent_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_received = received_transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    # Merge and sort by timestamp
    all_transactions   = (sent_transactions | received_transactions).order_by('-timestamp')
    recent_transactions = all_transactions[:10]

    # ── Expense Doughnut Chart Data ───────────────────────────────────────────
    expenses_by_category = (
        sent_transactions
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    expense_labels = [item['category'] for item in expenses_by_category]
    expense_data   = [float(item['total']) for item in expenses_by_category]

    # ── Balance Trend (Line Chart) ────────────────────────────────────────────
    trend_labels = []
    trend_data   = []

    if all_transactions.exists():
        current_bal = float(user.balance)
        historical_balances = [current_bal]
        labels = ["Now"]

        for txn in recent_transactions:
            if txn.sender == user:
                current_bal += float(txn.amount)   # reverse the deduction
            else:
                current_bal -= float(txn.amount)   # reverse the credit
            historical_balances.insert(0, round(current_bal, 2))
            labels.insert(0, txn.timestamp.strftime("%b %d, %H:%M"))

        trend_data   = historical_balances
        trend_labels = labels

    # ── Loan Data ─────────────────────────────────────────────────────────────
    active_loans      = LoanRequest.objects.filter(user=user).order_by('-created_at')
    pending_all_loans = (
        LoanRequest.objects.filter(status='Pending').order_by('-created_at')
        if user.is_superuser else None
    )

    # ── Transfer Form (for non-AJAX fallback) ────────────────────────────────
    transfer_form = TransferForm()

    context = {
        'transfer_form':       transfer_form,
        'total_sent':          total_sent,
        'total_received':      total_received,
        'recent_transactions': recent_transactions,
        'expense_labels':      json.dumps(expense_labels),
        'expense_data':        json.dumps(expense_data),
        'trend_labels':        json.dumps(trend_labels),
        'trend_data':          json.dumps(trend_data),
        'active_loans':        active_loans,
        'pending_all_loans':   pending_all_loans,
    }
    return render(request, 'core/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFER PAGE (traditional form-based, full-page)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def transfer_money(request):
    """
    Traditional (non-AJAX) money transfer page.
    Kept for accessibility / non-JS fallback.
    """
    user = request.user

    if request.method == 'POST':
        transfer_form = TransferForm(request.POST)
        if transfer_form.is_valid():
            recipient_roll = transfer_form.cleaned_data['recipient_roll_number']
            amount         = transfer_form.cleaned_data['amount']
            category       = transfer_form.cleaned_data['category']

            if recipient_roll == user.roll_number:
                messages.error(request, "You cannot transfer money to yourself.")
            elif user.balance < amount:
                messages.error(request, "Insufficient balance.")
            else:
                try:
                    with db_transaction.atomic():
                        sender    = BankUser.objects.select_for_update().get(id=user.id)
                        recipient = BankUser.objects.select_for_update().get(roll_number=recipient_roll)

                        sender.balance    -= amount
                        recipient.balance += amount
                        sender.save()
                        recipient.save()

                        Transaction.objects.create(
                            sender=sender,
                            receiver=recipient,
                            amount=amount,
                            category=category,
                            transaction_type='Transfer',
                        )
                    messages.success(
                        request,
                        f"Successfully transferred ₹{amount} to {recipient.name} ({recipient.roll_number})."
                    )
                    return redirect('dashboard')
                except BankUser.DoesNotExist:
                    messages.error(request, "Recipient not found.")
                except Exception as e:
                    messages.error(request, f"An error occurred: {str(e)}")
        else:
            for field, errors in transfer_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        transfer_form = TransferForm()

    return render(request, 'core/transfer.html', {'transfer_form': transfer_form})


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: SEND MONEY
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def send_money_api(request):
    """
    AJAX endpoint for the dashboard Send Money form.
    
    POST Body (JSON):
        { "roll_number": "12345", "amount": 500.00, "category": "Canteen" }

    Returns:
        { "success": true, "new_balance": 9500.00, "message": "..." }
        { "success": false, "message": "..." }
    """
    try:
        data           = json.loads(request.body)
        recipient_roll = data.get('roll_number', '').strip()
        amount_raw     = data.get('amount', 0)
        category       = data.get('category', 'General')
        note           = data.get('note', '')

        # ── Validation ────────────────────────────────────────────────────────
        try:
            amount = Decimal(amount_raw)
        except (TypeError, ValueError):
            return _json_error("Invalid amount.")

        if amount <= 0:
            return _json_error("Amount must be greater than zero.")

        if not recipient_roll:
            return _json_error("Recipient roll number is required.")

        if recipient_roll == request.user.roll_number:
            return _json_error("You cannot transfer money to yourself.")

        # ── Atomic Transfer ───────────────────────────────────────────────────
        with db_transaction.atomic():
            sender = BankUser.objects.select_for_update().get(id=request.user.id)

            if sender.balance < amount:
                return _json_error(
                    f"Insufficient balance. Your balance is ₹{sender.balance}."
                )

            try:
                recipient = BankUser.objects.select_for_update().get(
                    roll_number=recipient_roll,
                    is_active=True
                )
            except BankUser.DoesNotExist:
                return _json_error("Recipient not found or account not active.")

            sender.balance    -= amount
            recipient.balance += amount
            sender.save(update_fields=['balance'])
            recipient.save(update_fields=['balance'])

            txn = Transaction.objects.create(
                sender=sender,
                receiver=recipient,
                amount=amount,
                category=category,
                transaction_type='Transfer',
                note=note,
            )

        return _json_ok({
            'message':     f"₹{amount:.2f} sent to {recipient.name} ({recipient.roll_number}).",
            'new_balance': float(sender.balance),
            'txn_id':      txn.id,
            'timestamp':   txn.timestamp.strftime('%b %d, %H:%M'),
        })

    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: BILL SPLIT
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def bill_split_api(request):
    """
    AJAX endpoint for the Bill Splitter.
    Splits a total bill equally among the current user and listed friends,
    debiting the current user's account and crediting each friend's account.

    POST Body (JSON):
        {
            "total_amount": 600.00,
            "friends": ["12346", "12347"],
            "category": "Canteen",
            "note": "Dinner at hostel canteen"
        }

    Returns:
        { "success": true, "message": "...", "per_person": 200.00, "new_balance": 9400.00 }
    """
    try:
        data         = json.loads(request.body)
        total_amount = float(data.get('total_amount', 0))
        friends_raw  = data.get('friends', [])
        category     = data.get('category', 'General')
        note         = data.get('note', 'Bill Split')

        # ── Validation ────────────────────────────────────────────────────────
        if total_amount <= 0:
            return _json_error("Total bill amount must be greater than zero.")

        # Clean and de-duplicate friend roll numbers, removing self
        friend_rolls = list({
            r.strip() for r in friends_raw
            if r.strip() and r.strip() != request.user.roll_number
        })

        if not friend_rolls:
            return _json_error("Please provide at least one friend's roll number.")

        total_people = len(friend_rolls) + 1  # friends + current user
        per_person   = round(total_amount / total_people, 2)

        # ── Atomic Multi-Transfer ─────────────────────────────────────────────
        with db_transaction.atomic():
            sender = BankUser.objects.select_for_update().get(id=request.user.id)

            # The sender pays (total_people - 1) shares = total - own_share
            sender_deduction = round(per_person * len(friend_rolls), 2)

            if sender.balance < sender_deduction:
                return _json_error(
                    f"Insufficient balance. You need ₹{sender_deduction:.2f} to cover your friends' shares. "
                    f"Your balance: ₹{sender.balance}."
                )

            # Validate all friends exist and are active before touching balances
            recipients = []
            for roll in friend_rolls:
                try:
                    r = BankUser.objects.select_for_update().get(
                        roll_number=roll, is_active=True
                    )
                    recipients.append(r)
                except BankUser.DoesNotExist:
                    return _json_error(
                        f"User with roll number '{roll}' not found or not active."
                    )

            # Perform transfers
            sender.balance -= sender_deduction
            sender.save(update_fields=['balance'])

            for recipient in recipients:
                recipient.balance += per_person
                recipient.save(update_fields=['balance'])

                Transaction.objects.create(
                    sender=sender,
                    receiver=recipient,
                    amount=per_person,
                    category=category,
                    transaction_type='Bill Split',
                    note=note,
                )

        return _json_ok({
            'message':     (
                f"Bill split done! ₹{per_person:.2f} sent to each of "
                f"{len(recipients)} friends."
            ),
            'per_person':  per_person,
            'total_people': total_people,
            'new_balance': float(sender.balance),
        })

    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: LOAN — APPLY
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def apply_loan_api(request):
    """
    AJAX endpoint to submit a new loan request.

    POST Body (JSON):
        { "amount": 5000.00, "purpose": "Semester books" }

    Returns:
        { "success": true, "loan_id": 3, "amount": 5000.0, ... }
    """
    try:
        data    = json.loads(request.body)
        amount  = float(data.get('amount', 0))
        purpose = data.get('purpose', '').strip()

        if amount <= 0:
            return _json_error("Loan amount must be greater than zero.")
        if not purpose:
            return _json_error("Purpose is required.")

        loan = LoanRequest.objects.create(
            user=request.user,
            amount=amount,
            purpose=purpose
        )

        return _json_ok({
            'loan_id':    loan.id,
            'amount':     float(loan.amount),
            'purpose':    loan.purpose,
            'status':     loan.status,
            'created_at': loan.created_at.strftime('%b %d, %H:%M'),
        })

    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: LOAN — APPROVE / REJECT  (Admin only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def approve_loan_api(request):
    """
    AJAX endpoint (superuser only) to approve or reject a pending loan.

    POST Body (JSON):
        { "loan_id": 3, "status": "Approved" }  |  "Rejected"

    On Approval: credits the loan amount to the applicant's balance.
    """
    if not request.user.is_superuser:
        return _json_error("Permission denied.", status=403)

    try:
        data    = json.loads(request.body)
        loan_id = data.get('loan_id')
        status  = data.get('status')

        if status not in ('Approved', 'Rejected'):
            return _json_error("Status must be 'Approved' or 'Rejected'.")

        with db_transaction.atomic():
            loan = LoanRequest.objects.select_for_update().get(id=loan_id)

            if loan.status != 'Pending':
                return _json_error("Loan is already processed.")

            loan.status = status
            loan.save(update_fields=['status'])

            if status == 'Approved':
                # Credit the loan amount atomically
                applicant = BankUser.objects.select_for_update().get(id=loan.user.id)
                applicant.balance += loan.amount
                applicant.save(update_fields=['balance'])

                # Log as a Loan transaction (system → applicant)
                Transaction.objects.create(
                    sender=request.user,    # admin/system user
                    receiver=applicant,
                    amount=loan.amount,
                    category='General',
                    transaction_type='Loan',
                    note=f"Loan #{loan.id} approved",
                )

        return _json_ok({'message': f"Loan #{loan_id} has been {status.lower()}."})

    except LoanRequest.DoesNotExist:
        return _json_error("Loan request not found.", status=404)
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: FACE LOGIN VERIFY
# ─────────────────────────────────────────────────────────────────────────────

def face_login_verify(request):
    """
    Mock biometric authentication endpoint.

    How the simulation works:
    1. Frontend captures a video frame and sends the user's self-reported roll_number.
    2. Backend looks up the user, checks they're active, then calls Django's auth_login().
    3. Returns JSON { success: true, redirect: '/dashboard/' } which JS uses to navigate.

    In a real system this would verify a face embedding against stored face_signature.
    The face_signature field is seeded with a SHA-256 hash of the roll_number for demo purposes.

    POST Body (JSON):
        { "roll_number": "12345" }
    """
    if request.method != 'POST':
        return _json_error("POST required.", status=405)

    try:
        data        = json.loads(request.body)
        roll_number = data.get('roll_number', '').strip()

        if not roll_number:
            return _json_error("Roll number is required for biometric verification.")

        # ── Look up user ──────────────────────────────────────────────────────
        try:
            user = BankUser.objects.get(roll_number=roll_number)
        except BankUser.DoesNotExist:
            return _json_error("No account found with that roll number.")

        if not user.is_active:
            return _json_error("Account is not yet activated. Please contact admin.")

        # ── Mock biometric check ──────────────────────────────────────────────
        # Generate or compare face_signature (SHA-256 of roll_number as mock)
        mock_hash = hashlib.sha256(roll_number.encode()).hexdigest()

        if user.face_signature:
            # Signature already stored — compare
            if user.face_signature != mock_hash:
                return _json_error("Biometric verification failed.")
        else:
            # First-time FaceID: store the mock hash (enroll)
            user.face_signature = mock_hash
            user.save(update_fields=['face_signature'])

        # ── Log the user in ───────────────────────────────────────────────────
        # We bypass the normal authentication backend check since this is a
        # biometric (non-password) flow. We must specify the backend explicitly.
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)

        return _json_ok({
            'message':  f"Welcome back, {user.name}!",
            'redirect': '/dashboard/',
        })

    except json.JSONDecodeError:
        return _json_error("Invalid JSON body.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: GET MY QR CODE DATA
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_GET
def get_user_qr(request):
    """
    Returns the authenticated user's roll number as plain text.
    The frontend uses this to generate an on-screen QR code via qrcode.js.

    Response:
        { "success": true, "roll_number": "12345", "name": "Nishtha Shukla" }
    """
    return _json_ok({
        'roll_number': request.user.roll_number,
        'name':        request.user.name,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CSV STATEMENT DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def download_statement(request):
    """
    Generates and streams a CSV account statement for the logged-in user.
    """
    user = request.user
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="MUDRA_Statement_{user.roll_number}.csv"'
    )

    writer = csv.writer(response)

    # Header block
    writer.writerow(['MUDRA — Campus Fintech Platform — Account Statement'])
    writer.writerow(['Account Holder:', user.name])
    writer.writerow(['Roll Number:',    user.roll_number])
    writer.writerow(['Generated On:',   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])

    # Column headers
    writer.writerow(['Date & Time', 'Type', 'Category', 'Amount (INR)', 'Counterparty', 'Note'])

    sent_txns = Transaction.objects.filter(sender=user)
    recv_txns = Transaction.objects.filter(receiver=user)
    all_txns  = (sent_txns | recv_txns).order_by('-timestamp')

    for txn in all_txns:
        if txn.sender == user:
            txn_type     = "Debit (Sent)"
            counterparty = txn.receiver.roll_number
        else:
            txn_type     = "Credit (Received)"
            counterparty = txn.sender.roll_number

        writer.writerow([
            txn.timestamp.strftime("%Y-%m-%d %H:%M"),
            txn_type,
            txn.category,
            f"Rs. {txn.amount}",
            counterparty,
            txn.note,
        ])

    writer.writerow([])
    writer.writerow(['Current Balance:', f"Rs. {user.balance}"])
    writer.writerow(['— End of Statement —'])

    return response
def legal_view(request):
    return render(request, 'core/legal.html') 
 
@login_required
def balances(request):
    return render(request, 'core/balances.html')

@login_required
def statements(request):
    return render(request, 'core/statements.html')

@login_required
def send_money_page(request):
    return render(request, 'core/send_money.html')

@login_required
def beneficiaries(request):
    return render(request, 'core/beneficiaries.html')

@login_required
def fee_payment(request):
    return render(request, 'core/fee_payment.html')

@login_required
def virtual_card(request):
    return render(request, 'core/virtual_card.html')

@login_required
def helpdesk(request):
    return render(request, 'core/helpdesk.html')