import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure PaymentRequest is imported
if 'PaymentRequest' not in content:
    content = content.replace('from .models import BankUser, Transaction, LoanRequest', 'from .models import BankUser, Transaction, LoanRequest, PaymentRequest')

old_split = """        # ── Atomic Multi-Transfer ─────────────────────────────────────────────
        with db_transaction.atomic():
            sender = BankUser.objects.select_for_update().get(id=request.user.id)

            # The sender pays (total_people - 1) shares = total - own_share
            sender_deduction = round(per_person * len(friend_rolls), 2)

            if sender.wallet_balance < sender_deduction:
                return _json_error(
                    f"Insufficient balance. You need ₹{sender_deduction:.2f} to cover your friends' shares. "
                    f"Your balance: ₹{sender.wallet_balance}."
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
            sender.wallet_balance -= sender_deduction
            sender.save(update_fields=['wallet_balance'])

            for recipient in recipients:
                recipient.wallet_balance += per_person
                recipient.save(update_fields=['wallet_balance'])

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
            'new_balance': float(sender.wallet_balance),
        })"""

new_split = """        # ── Atomic Multi-Transfer -> Now Payment Requests ────────────────────────
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
        })"""

content = content.replace(old_split, new_split)

new_apis = """
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

                Transaction.objects.create(
                    sender=payer,
                    receiver=requester,
                    amount=pay_req.amount,
                    category='General',
                    transaction_type='Bill Split',
                    note=pay_req.note,
                )
                
                return _json_ok({'message': "Payment approved and sent successfully.", 'new_balance': float(payer.wallet_balance)})
            else:
                return _json_error("Invalid action.")
    except PaymentRequest.DoesNotExist:
        return _json_error("Request not found.")
    except Exception as e:
        return _json_error(f"Server error: {str(e)}", status=500)
"""

if 'def respond_payment_api' not in content:
    content += new_apis

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('views updated!')
