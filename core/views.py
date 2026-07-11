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

from .models import BankUser, Transaction, LoanRequest, PaymentRequest, SupportTicket
from .forms import BankUserCreationForm, TransferForm
from decimal import Decimal

import json
import csv
import datetime
import hashlib
import math


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
            
            face_desc_raw = request.POST.get('face_descriptor', '')
            if face_desc_raw:
                try:
                    desc_list = json.loads(face_desc_raw)
                    if isinstance(desc_list, list) and len(desc_list) == 128:
                        user.face_signature = json.dumps(desc_list)
                except Exception:
                    pass
                    
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
        # current_bal = float(user.wallet_balance)
        current_bal = float(user.wallet_balance)
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
    pending_requests = PaymentRequest.objects.filter(payer=user, status='Pending').order_by('-created_at')

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
        'pending_requests': pending_requests,
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
            # elif user.wallet_balance < amount:
            elif user.wallet_balance < amount:
                messages.error(request, "Insufficient balance.")
            else:
                try:
                    with db_transaction.atomic():
                        sender    = BankUser.objects.select_for_update().get(id=user.id)
                        recipient = BankUser.objects.select_for_update().get(roll_number=recipient_roll)

                        sender.wallet_balance    -= amount
                        recipient.wallet_balance += amount
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
    pending_requests = PaymentRequest.objects.filter(payer=user, status='Pending').order_by('-created_at')

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

            if sender.wallet_balance < amount:
                return _json_error(
                    f"Insufficient balance. Your balance is ₹{sender.wallet_balance}."
                )

            try:
                recipient = BankUser.objects.select_for_update().get(
                    roll_number=recipient_roll,
                    is_active=True
                )
            except BankUser.DoesNotExist:
                return _json_error("Recipient not found or account not active.")

            sender.wallet_balance    -= amount
            recipient.wallet_balance += amount
            sender.save(update_fields=['wallet_balance'])
            recipient.save(update_fields=['wallet_balance'])

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
            'new_balance': float(sender.wallet_balance),
            'txn_id':      txn.id,
            'timestamp':   txn.timestamp.strftime('%b %d, %H:%M'),
            'amount':      float(amount),
            'category':    category,
            'receiver_name': recipient.name,
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

        # ── Atomic Multi-Transfer -> Now Payment Requests ────────────────────────
        with db_transaction.atomic():
            sender = request.user

            # Validate all friends exist and are active
            recipients = []
            for roll in friend_rolls:
                try:
                    r = BankUser.objects.get(
                        roll_number=roll, is_active=True
                    )
                    recipients.append(r)
                except BankUser.DoesNotExist:
                    return _json_error(
                        f"User with roll number '{roll}' not found or not active."
                    )

            # Create payment requests (sender is requesting money from friends)
            for recipient in recipients:
                PaymentRequest.objects.create(
                    requester=sender,
                    payer=recipient,
                    amount=per_person,
                    note=note
                )

        return _json_ok({
            'message':     (
                f"Payment requests of ₹{per_person:.2f} sent to "
                f"{len(recipients)} friends."
            ),
            'per_person':  per_person,
            'total_people': total_people,
            'new_balance': float(sender.wallet_balance),
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
                applicant.wallet_balance += loan.amount
                applicant.save(update_fields=['wallet_balance'])

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
        descriptor = data.get('descriptor', None)

        if not roll_number or not descriptor:
            return _json_error("Roll number and face descriptor are required.")

        # ── Look up user ──────────────────────────────────────────────────────
        try:
            user = BankUser.objects.get(roll_number=roll_number)
        except BankUser.DoesNotExist:
            return _json_error("No account found with that roll number.")

        if not user.is_active:
            return _json_error("Account is not yet activated. Please contact admin.")

        # ── Biometric check ──────────────────────────────────────────────
        if user.face_signature:
            try:
                stored_descriptor = json.loads(user.face_signature)
                if len(stored_descriptor) != 128 or len(descriptor) != 128:
                    return _json_error("Invalid biometric data.")
                    
                # Calculate Euclidean distance
                distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(stored_descriptor, descriptor)))
                
                # Face-api.js usually recommends a threshold of 0.6
                if distance > 0.55:
                    return _json_error("Face does not match. Please try again.")
            except Exception as e:
                return _json_error("Error reading stored biometrics. Please re-register.")
        else:
            return _json_error("Face Unlock is not set up for this account. Please login with password and register FaceID from the dashboard.")

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
# AJAX API: REGISTER FACEID
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def register_face_api(request):
    try:
        data = json.loads(request.body)
        descriptor = data.get('descriptor')
        
        if not descriptor or len(descriptor) != 128:
            return _json_error("Invalid face descriptor. Please make sure your face is clearly visible.")
            
        user = request.user
        user.face_signature = json.dumps(descriptor)
        user.save(update_fields=['face_signature'])
        
        return _json_ok({'message': "Face Unlock successfully registered!"})
    except json.JSONDecodeError:
        return _json_error("Invalid JSON.")
    except Exception as e:
        return _json_error(f"Error: {str(e)}")


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
    # writer.writerow(['Current Balance:', f"Rs. {user.wallet_balance}"])
    writer.writerow(['Current Balance:', f"Rs. {user.wallet_balance}"])
    writer.writerow(['— End of Statement —'])

    return response
def legal_view(request):
    return render(request, 'core/legal.html') 
 
@login_required
def balances(request):
    user = request.user
    sent_transactions = Transaction.objects.filter(sender=user)
    received_transactions = Transaction.objects.filter(receiver=user)
    total_spent = sent_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    total_received = received_transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'core/balances.html', {
        'total_spent': total_spent,
        'total_received': total_received
    })

@login_required
def statements(request):
    user = request.user
    sent_txns = Transaction.objects.filter(sender=user)
    recv_txns = Transaction.objects.filter(receiver=user)
    all_txns  = (sent_txns | recv_txns).order_by('-timestamp')
    return render(request, 'core/statements.html', {
        'transactions': all_txns
    })

@login_required
def send_money_page(request):
    return render(request, 'core/send_money.html')

@login_required
def beneficiaries(request):
    user = request.user
    # Get distinct receivers from sent transactions
    sent_txns = Transaction.objects.filter(sender=user).select_related('receiver')
    # Use a dictionary to keep unique recipients
    beneficiaries_dict = {}
    for txn in sent_txns:
        if txn.receiver.roll_number not in beneficiaries_dict:
            beneficiaries_dict[txn.receiver.roll_number] = txn.receiver
            
    return render(request, 'core/beneficiaries.html', {
        'beneficiaries': beneficiaries_dict.values()
    })

@login_required
def fee_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_val = float(data.get('amount', 0))
            amount = Decimal(str(amount_val))
            fee_type = data.get('fee_type', 'Tuition Fee')
            
            if amount <= 0:
                return _json_error("Amount must be greater than zero.")
                
            with db_transaction.atomic():
                user = BankUser.objects.select_for_update().get(id=request.user.id)
                if user.wallet_balance < amount:
                    return _json_error("Insufficient balance for this payment.")
                    
                user.wallet_balance -= amount
                user.save(update_fields=['wallet_balance'])
                
                # System (admin) is the receiver for fee
                admin_user = BankUser.objects.filter(is_superuser=True).first()
                if not admin_user:
                    admin_user = user # fallback to self if no admin exists
                    
                Transaction.objects.create(
                    sender=user,
                    receiver=admin_user,
                    amount=amount,
                    category='Education',
                    transaction_type='Transfer',
                    note=fee_type
                )
                
            return _json_ok({
                'message': f"{fee_type} of ₹{amount} paid successfully.",
                'new_balance': float(user.wallet_balance)
            })
            
        except Exception as e:
            return _json_error(f"Error processing payment: {str(e)}")
            
    return render(request, 'core/fee_payment.html')

@login_required
def virtual_card(request):
    user = request.user
    # 7-day balance trend mock data
    trend_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    current_bal = float(user.wallet_balance)
    trend_data = [
        max(0, current_bal - 400), max(0, current_bal - 300), max(0, current_bal - 250),
        max(0, current_bal - 200), max(0, current_bal - 150), max(0, current_bal - 50), current_bal
    ]
    
    context = {
        'trend_labels': trend_labels,
        'trend_data': trend_data,
    }
    return render(request, 'core/virtual_card.html', context)

@login_required
def helpdesk(request):
    user = request.user
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', '').strip()
        priority = request.POST.get('priority', 'Medium').strip()
        description = request.POST.get('description', '').strip()
        
        if subject and category and description:
            # Generate a unique ticket ID (BNK-TKT-XXXXXX)
            import random
            import time
            ticket_id = f"BNK-TKT-{int(time.time())}{random.randint(10, 99)}"
            
            SupportTicket.objects.create(
                user=user,
                ticket_id=ticket_id,
                subject=subject,
                category=category,
                priority=priority.capitalize(),
                description=description
            )
            messages.success(request, f"Ticket {ticket_id} submitted successfully.")
            return redirect('helpdesk')
        else:
            messages.error(request, "Please fill out all required fields.")

    # GET request: fetch tickets and stats
    tickets = SupportTicket.objects.filter(user=user)
    open_count = tickets.filter(status='Open').count() + tickets.filter(status='In Progress').count()
    resolved_count = tickets.filter(status='Resolved').count()

    context = {
        'tickets': tickets,
        'open_count': open_count,
        'resolved_count': resolved_count
    }
    return render(request, 'core/helpdesk.html', context)

def verify_roll_number(request):
    roll = request.GET.get('roll_number', '')
    if len(roll) == 13:
        try:
            user = BankUser.objects.get(roll_number=roll)
            name = user.name
            return JsonResponse({'success': True, 'name': name})
        except BankUser.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Account not found!'})
    return JsonResponse({'success': False, 'message': 'Invalid length'})
# ─────────────────────────────────────────────────────────────────────────────
# AJAX API: PAYMENT REQUEST APPROVE/DECLINE
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def respond_payment_api(request):
    try:
        data = json.loads(request.body)
        req_id = data.get('request_id')
        action = data.get('action') # 'approve' or 'decline'

        with db_transaction.atomic():
            pay_req = PaymentRequest.objects.select_for_update().get(id=req_id, payer=request.user)

            if pay_req.status != 'Pending':
                return _json_error("This request is already processed.")

            if action == 'decline':
                pay_req.status = 'Declined'
                pay_req.save(update_fields=['status'])
                return _json_ok({'message': "Payment request declined."})
            elif action == 'approve':
                if request.user.wallet_balance < pay_req.amount:
                    return _json_error("Insufficient balance to approve this request.")
                
                # Transfer money
                payer = BankUser.objects.select_for_update().get(id=request.user.id)
                requester = BankUser.objects.select_for_update().get(id=pay_req.requester.id)

                payer.wallet_balance -= pay_req.amount
                requester.wallet_balance += pay_req.amount
                payer.save(update_fields=['wallet_balance'])
                requester.save(update_fields=['wallet_balance'])

                pay_req.status = 'Paid'
                pay_req.save(update_fields=['status'])

                txn = Transaction.objects.create(
                    sender=payer,
                    receiver=requester,
                    amount=pay_req.amount,
                    category='General',
                    transaction_type='Bill Split',
                    note=pay_req.note,
                )
                
                return _json_ok({
                    'message': "Payment approved and sent successfully.", 
                    'new_balance': float(payer.wallet_balance),
                    'amount': float(pay_req.amount),
                    'category': 'General',
                    'receiver_name': requester.name,
                    'timestamp': txn.timestamp.strftime('%b %d, %H:%M')
                })
            else:
                return _json_error("Invalid action.")
    except PaymentRequest.DoesNotExist:
        return _json_error("Request not found.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)

def terms_view(request):
    return render(request, 'core/terms.html')

def privacy_view(request):
    return render(request, 'core/privacy.html')

def security_view(request):
    return render(request, 'core/security.html')
