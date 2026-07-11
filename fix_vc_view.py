import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_vc = "def virtual_card(request):\n    return render(request, 'core/virtual_card.html')"

new_vc = """@login_required
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
    return render(request, 'core/virtual_card.html', context)"""

if old_vc in content:
    content = content.replace(old_vc, new_vc)
else:
    # try replacing without exact whitespace
    import re
    content = re.sub(r'def virtual_card\(request\):\s*return render\(request, \'core/virtual_card\.html\'\)', new_vc, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('virtual_card view updated!')
