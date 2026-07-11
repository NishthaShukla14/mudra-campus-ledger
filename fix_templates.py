import os

files = {
    r'c:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\dashboard.html': [
        ('{{ user.balance|default:"0.00" }}', '{{ user.wallet_balance|default:"0.00" }}'),
        ('{{ user.balance|default:"0" }}', '{{ user.wallet_balance|default:"0" }}'),
        ('4532  1245  7890  3021', '{{ request.user.card_number }}')
    ],
    r'c:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\virtual_card.html': [
        ('4532 9811 0042 7831', '{{ request.user.card_number }}'),
        ('<div class="font-black text-2xl tracking-widest italic drop-shadow-sm">MUDRA</div>', '<div class="font-black text-2xl tracking-widest italic drop-shadow-sm">MUDRA</div>\n          <div class="text-xl font-bold font-mono mt-1" id="liveBalance">₹{{ request.user.wallet_balance }}</div>')
    ],
    r'c:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\balances.html': [
        ('>₹12,450<', '>₹{{ request.user.wallet_balance }}<')
    ]
}

for path, replacements in files.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Templates updated!')
