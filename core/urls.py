from django.contrib import admin
from django.urls import path
from account import views
from django.conf import settings
from django.conf.urls import handler404, handler500

urlpatterns = [
    # --- ADMIN PANEL ---
    path('admin/', admin.site.urls),
    
    # --- PUBLIC PAGES ---
    path('', views.home, name='home'),
    path('about/', views.about_view, name='about'),
    path('security-center/', views.security_info_view, name='security'),
    path('business/', views.business_view, name='business'),
    path('help/', views.help_center_view, name='help'),

    # --- AUTHENTICATION ---
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp-verify/', views.otp_view, name='otp_verify'),
    path('forgot-access/', views.forgot_access_view, name='forgot_access'),
    path('recover-otp/', views.recover_otp_view, name='recover_otp'),
    path('reset-access/', views.reset_access_view, name='reset_access'),
    
    # --- SECURITY ---
    path('create-pin/', views.create_pin, name='create_pin'),
    path('transfer-otp/', views.transfer_otp, name='transfer_otp'),
    path('toggle-preference/', views.toggle_preference, name='toggle_preference'),
    
    # --- BANKING CORE ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transfer/', views.transfer_money, name='transfer'),
    path('profile/', views.profile_view, name='profile'),
    path('kyc/', views.kyc_upload_view, name='kyc'),
    path('cards/', views.card_detail, name='cards'),
    path('transaction/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('transaction/<int:transaction_id>/receipt/', views.transaction_receipt, name='transaction_receipt'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('pay-bills/', views.pay_bills, name='pay_bills'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('loans/', views.loans_view, name='loans'),
    path('support/', views.support_view, name='support'),
    path('settings/', views.settings_view, name='settings'),
    
    # --- DOCUMENTS ---
    path('documents/', views.documents_view, name='documents'),
    path('statement/', views.statement_view, name='statement'),
    
    # --- UTILS ---
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('notifications/delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
]

handler404 = 'account.views.custom_404'
handler500 = 'account.views.custom_500'