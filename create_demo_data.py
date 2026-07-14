import os
import django
from decimal import Decimal
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acad_vault.settings')
django.setup()

from core.models import BankUser, Transaction
from django.utils import timezone

def create_demo_data():
    demo_roll = '2401229999999'
    demo_user, created = BankUser.objects.get_or_create(
        roll_number=demo_roll,
        defaults={'name': 'Demo User', 'wallet_balance': Decimal('15000.00')}
    )
    if created:
        demo_user.set_password('demo2026!')
        demo_user.save()
        print(f"Created demo user: {demo_roll} / demo2026!")
    else:
        print(f"Demo user already exists: {demo_roll} / demo2026!")
        demo_user.set_password('demo2026!')
        demo_user.wallet_balance = Decimal('15000.00')
        demo_user.save()

    peers = []
    for i in range(1, 6):
        roll = f'240122888888{i}'
        peer, c = BankUser.objects.get_or_create(
            roll_number=roll,
            defaults={'name': f'Demo Peer {i}', 'wallet_balance': Decimal('5000.00')}
        )
        if c:
            peer.set_password('peer2026!')
            peer.save()
        peers.append(peer)

    Transaction.objects.filter(sender=demo_user).delete()
    Transaction.objects.filter(receiver=demo_user).delete()

    transaction_templates = {
        'Mess Fee': [('Monthly Mess Bill', 2500, 3500), ('Mess Advance', 1000, 2000), ('Guest Meal', 150, 300)],
        'Canteen': [('Coffee & Snacks', 40, 150), ('Lunch at Canteen', 100, 250), ('Cold drinks', 30, 80)],
        'Books': [('Engineering Physics Book', 400, 800), ('Stationery', 50, 200), ('Library Fine', 10, 50)],
        'Hostel': [('Hostel Maintenance', 500, 1500), ('Room Cooler Bill', 300, 600)],
        'General': [('Movie Tickets Split', 200, 500), ('Uber fare split', 150, 400), ('Birthday Gift', 300, 800)]
    }

    types = ['Transfer', 'Bill Split', 'Loan']

    for i in range(50):
        peer = random.choice(peers)
        is_sender = random.choice([True, False])
        category = random.choice(list(transaction_templates.keys()))
        
        template = random.choice(transaction_templates[category])
        note_text, min_amt, max_amt = template
        amount = Decimal(random.randint(min_amt, max_amt))
        
        txn_type = random.choice(types)
        
        if is_sender:
            sender = demo_user
            receiver = peer
            demo_user.wallet_balance -= amount
            peer.wallet_balance += amount
        else:
            sender = peer
            receiver = demo_user
            peer.wallet_balance -= amount
            demo_user.wallet_balance += amount
            
        txn = Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            category=category,
            transaction_type=txn_type,
            note=note_text
        )
        
        days_ago = random.randint(0, 90)
        past_date = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        Transaction.objects.filter(id=txn.id).update(timestamp=past_date)

    demo_user.save()
    for p in peers:
        p.save()

    print("Demo data generated successfully!")

if __name__ == '__main__':
    create_demo_data()
