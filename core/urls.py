"""
MUDRA - Campus Fintech Application
urls.py — URL routing for core app
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    # ── Public Pages ──────────────────────────────────────────────────────────
    path('',        views.home,        name='home'),
    path('signup/', views.signup_view, name='signup'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='core/login.html'),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout'
    ),

    # ── Authenticated Pages ───────────────────────────────────────────────────
    path('dashboard/', views.dashboard,      name='dashboard'),
    path('transfer/',  views.transfer_money, name='transfer_money'),

    # ── Download ──────────────────────────────────────────────────────────────
    path('download-statement/', views.download_statement, name='download_statement'),

    # ── AJAX JSON APIs ────────────────────────────────────────────────────────
    # Send Money (dashboard inline form → AJAX)
    path('api/send-money/',    views.send_money_api,     name='send_money_api'),

    # Bill Splitter (dashboard → AJAX)
    path('api/bill-split/',    views.bill_split_api,     name='bill_split_api'),

    # Loan: apply (student) and approve/reject (admin)
    path('api/loan/apply/',    views.apply_loan_api,     name='apply_loan_api'),
    path('api/loan/approve/',  views.approve_loan_api,   name='approve_loan_api'),

    # FaceID biometric mock login
    path('api/face-login/',    views.face_login_verify,  name='face_login_verify'),

    # QR code data for logged-in user
    path('api/my-qr/',         views.get_user_qr,        name='get_user_qr'),
    path('balances/', views.balances, name='balances'),
    path('statements/', views.statements, name='statements'),
    path('send-money/', views.send_money_page, name='send_money_page'),
    path('beneficiaries/', views.beneficiaries, name='beneficiaries'),
    path('fee-payment/', views.fee_payment, name='fee_payment'),
    path('virtual-card/', views.virtual_card, name='virtual_card'),
    path('helpdesk/', views.helpdesk, name='helpdesk'),
]
path('legal/', views.legal_view, name='legal'),