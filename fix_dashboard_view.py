import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add pending requests to context
if 'pending_requests' not in content:
    content = content.replace("    transfer_form = TransferForm()", "    transfer_form = TransferForm()\n    pending_requests = PaymentRequest.objects.filter(payer=user, status='Pending').order_by('-created_at')")
    content = content.replace("'pending_all_loans':   pending_all_loans,", "'pending_all_loans':   pending_all_loans,\n        'pending_requests': pending_requests,")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Dashboard view updated!')
