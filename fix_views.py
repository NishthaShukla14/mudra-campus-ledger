import re

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix occurrences of .balance to .wallet_balance
content = content.replace('.balance', '.wallet_balance')
content = content.replace("['balance']", "['wallet_balance']")
content = content.replace('elif wallet_balance < amount:', 'elif user.wallet_balance < amount:')
content = content.replace('f"Rs. {wallet_balance}"', 'f"Rs. {user.wallet_balance}"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('views.py fixed!')
