from django.contrib import admin
from django.urls import path
from account import views
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500

# --- SPECIAL SETUP IMPORTS ---
from django.core.management import call_command
from django.contrib.auth.models import User
from django.http import HttpResponse

# --- SPECIAL SETUP VIEW ---
def setup_bank(request):
    try:
        # 1. Force Database Migration (Create Tables)
        call_command('migrate')
        
        # 2. Create Admin User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@veltris.com', 'Admin123!')
            return HttpResponse("<h1>SUCCESS!</h1><p>Database tables created.</p><p>Superuser created.</p><p><strong>Username:</strong> admin</p><p><strong>Password:</strong> Admin123!</p><a href='/admin/'>Go to Login</a>")
        else:
            return HttpResponse("<h1>Already Setup</h1><p>Admin account 'admin' already exists.</p><a href='/admin/'>Go to Login</a>")
    except Exception as e:
        return HttpResponse(f"<h1>Error</h1><p>{e}</p>")

urlpatterns = [
    # Special Setup Link
    path('setup-bank/', setup_bank),

    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    # Public
    path('about/', views.about_view, name='about'),
    path('security-center/', views.security_info_view, name='security'),
    path('business/', views.business_view, name='business'),
    path('help/', views.help_center_view, name='help'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp-verify/', views.otp_view, name='otp_verify'),
    path('forgot-access/', views.forgot_access_view, name='forgot_access'),
    path('recover-otp/', views.recover_otp_view, name='recover_otp'),
    path('reset-access/', views.reset_access_view, name='reset_access'),
    
    # Security
    path('create-pin/', views.create_pin, name='create_pin'),
    path('transfer-otp/', views.transfer_otp, name='transfer_otp'),
    path('toggle-preference/', views.toggle_preference, name='toggle_preference'),
    
    # Banking
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
    
    # Documents
    path('documents/', views.documents_view, name='documents'),
    path('statement/', views.statement_view, name='statement'),
    
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('notifications/delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
]

handler404 = 'account.views.custom_404'
handler500 = 'account.views.custom_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)