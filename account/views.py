from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Account, Transaction, CreditCard, Notification, SupportMessage, Loan
from django.db.models import Q, Sum
from django.contrib import messages
from decimal import Decimal
from django.contrib.auth.models import User
import uuid
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import HttpResponse

# ==========================================
# 1. PREMIUM EMAIL ENGINE
# ==========================================

def get_email_style():
    """Returns the CSS styles for premium emails."""
    return """
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        .header { background: #004d99; padding: 30px; text-align: center; }
        .header h1 { color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 2px; font-weight: 700; }
        .content { padding: 40px; }
        .amount-box { text-align: center; margin-bottom: 30px; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; }
        .label { font-size: 12px; text-transform: uppercase; color: #64748b; letter-spacing: 1px; margin-bottom: 5px; font-weight: 600; }
        .amount { font-size: 38px; font-weight: 800; color: #1a1a1a; letter-spacing: -1px; margin: 0; }
        .code-box { background: #eff6ff; border: 1px solid #dbeafe; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; }
        .code-val { font-size: 36px; font-weight: bold; color: #004d99; letter-spacing: 5px; display: block; }
        .status-badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; margin-top: 15px; }
        .status-success { background: #dcfce7; color: #166534; }
        .status-processing { background: #fef9c3; color: #854d0e; }
        .details-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .details-table td { padding: 12px 0; border-bottom: 1px solid #f1f5f9; color: #334155; font-size: 14px; }
        .details-table td:last-child { text-align: right; font-weight: 600; color: #1a1a1a; }
        .footer { background: #f8fafc; padding: 25px; text-align: center; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px; line-height: 1.6; }
    </style>
    """

def send_premium_otp(user, otp, action="verify your identity"):
    """Sends a secure, branded OTP email."""
    subject = f'{otp} is your Veltris verification code'
    html_content = f"""
    <!DOCTYPE html><html><head>{get_email_style()}</head><body>
    <div class="container">
        <div class="header"><h1>VELTRIS BANK</h1></div>
        <div class="content">
            <h2 style="color:#1a1a1a;margin-top:0;text-align:center;">Verification Required</h2>
            <p style="color:#666;font-size:15px;line-height:1.6;text-align:center;">
                Hello <strong>{user.first_name or user.username}</strong>,<br><br>
                You requested to <strong>{action}</strong>. Please use the secure code below to complete this action.
            </p>
            <div class="code-box">
                <span class="label" style="color:#64748b;display:block;margin-bottom:10px;">Security Code</span>
                <span class="code-val">{otp}</span>
            </div>
            <p style="color:#999;font-size:13px;text-align:center;">This code expires in 10 minutes. Do not share it with anyone.</p>
        </div>
        <div class="footer">&copy; 2025 Veltris Technologies Inc.<br>Secure Banking System</div>
    </div></body></html>
    """
    try:
        msg = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        print(f"Email Error: {e}")

def send_transaction_alert(user, amount, type, status):
    """Sends a digital receipt email for transactions."""
    if not hasattr(user, 'account') or not user.account.email_alerts: 
        return
    
    formatted_amount = "{:,.2f}".format(float(amount))
    status_color = "success" if status.lower() in ['success', 'successful'] else "processing"
    
    subject = f'Transaction Alert: {type.title()}'
    html_content = f"""
    <!DOCTYPE html><html><head>{get_email_style()}</head><body>
    <div class="container">
        <div class="header"><h1>VELTRIS BANK</h1></div>
        <div class="content">
            <div class="amount-box">
                <div class="label">Transaction Amount</div>
                <div class="amount">${formatted_amount}</div>
                <div class="status-badge status-{status_color}">{status.upper()}</div>
            </div>
            <p style="color:#666;font-size:14px;line-height:1.6;">
                <strong>Transaction Type:</strong> {type.title()}<br>
                <strong>Date:</strong> {timezone.now().strftime('%b %d, %Y - %I:%M %p')}<br>
                <strong>Account:</strong> Checking •••• {user.account.account_number[-4:]}<br>
                <strong>Reference:</strong> #TRX-{random.randint(100000,999999)}
            </p>
            <table class="details-table">
                <tr><td>Status</td><td>{status}</td></tr>
                <tr><td>Merchant/Recipient</td><td>Veltris Processing</td></tr>
            </table>
        </div>
        <div class="footer">
            &copy; 2025 Veltris Technologies Inc.<br>
            If you did not authorize this transaction, please contact support immediately.
        </div>
    </div></body></html>
    """
    try:
        msg = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        print(f"Email Error: {e}")


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def check_and_approve_transactions(user):
    """Automatically approves pending transactions older than 10 minutes (Simulation logic)."""
    time_threshold = timezone.now() - timedelta(minutes=10)
    pending_txns = Transaction.objects.filter(sender=user, status='processing', date__lt=time_threshold)
    for txn in pending_txns:
        txn.status = 'success'
        txn.save()
        send_transaction_alert(user, txn.amount, txn.transaction_type, 'Successful')
        
        # Credit receiver if it was a pending internal transfer
        if txn.transaction_type == 'internal' and txn.receiver:
            txn.receiver.account.balance += txn.amount
            txn.receiver.account.save()
            Notification.objects.create(user=txn.receiver, message=f"Credit Alert: You received ${txn.amount} from {user.username}.")
            send_transaction_alert(txn.receiver, txn.amount, "Incoming Transfer", "Successful")

# ==========================================
# 3. SETTINGS & PREFERENCES
# ==========================================

@login_required(login_url='/login/')
def settings_view(request):
    return render(request, 'account/settings.html', {'account': request.user.account})

@login_required(login_url='/login/')
def toggle_preference(request):
    if request.method == 'POST':
        field = request.POST.get('field')
        account = request.user.account
        
        if field == 'dark_mode': account.dark_mode = not account.dark_mode
        elif field == 'hide_balance': account.hide_balance = not account.hide_balance
        elif field == 'email_alerts': account.email_alerts = not account.email_alerts
        
        account.save()
        return HttpResponse(status=204)
    return HttpResponse(status=400)

# ==========================================
# 4. AUTHENTICATION & RECOVERY
# ==========================================

def home(request): return render(request, 'account/index.html')
def about_view(request): return render(request, 'account/about.html')
def security_info_view(request): return render(request, 'account/security_info.html')
def business_view(request): return render(request, 'account/business.html')
def help_center_view(request): return render(request, 'account/help_center.html')

def register_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm: 
            messages.error(request, "Passwords mismatch")
            return render(request, 'account/register.html')
        
        if User.objects.filter(username=username).exists(): 
            messages.error(request, "Username taken")
            return render(request, 'account/register.html')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        
        # Mapped form fields correctly to model fields
        Account.objects.create(
            user=user, balance=0.00, account_status='active',
            account_number=str(uuid.uuid4().int)[:10],
            phone=request.POST.get('phone'), address=request.POST.get('address'),
            city=request.POST.get('city'), zip_code=request.POST.get('zipcode'),
            date_of_birth=request.POST.get('dob'), ssn=request.POST.get('ssn'), 
            kyc_submitted=True, kyc_confirmed=False
        )
        messages.success(request, "Application received. Please sign in.")
        return redirect('login')
    return render(request, 'account/register.html')

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        identifier = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        user_obj = None
        if '@' in identifier:
            try: user_obj = User.objects.filter(email__iexact=identifier).first()
            except: pass
        else:
            try: user_obj = User.objects.filter(username__iexact=identifier).first()
            except: pass

        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)
            if user:
                otp = str(random.randint(100000, 999999))
                request.session['pre_login_id'] = user.id
                request.session['login_otp'] = otp
                if remember_me == 'on': request.session['remember_me'] = True
                send_premium_otp(user, otp, "log in to your account")
                return redirect('otp_verify')
        
        messages.error(request, "Invalid Credentials")
    return render(request, 'account/login.html')

def otp_view(request):
    if 'pre_login_id' not in request.session: return redirect('login')
    
    if request.method == 'POST':
        # RESEND LOGIC
        if 'resend_code' in request.POST:
            new_otp = str(random.randint(100000, 999999))
            request.session['login_otp'] = new_otp
            try:
                user = User.objects.get(id=request.session['pre_login_id'])
                send_premium_otp(user, new_otp, "log in (Resend)")
                messages.success(request, "New code sent.")
            except: pass
            return redirect('otp_verify')

        # VERIFY LOGIC
        if request.POST.get('otp_code') == request.session.get('login_otp'):
            user = User.objects.get(id=request.session['pre_login_id'])
            login(request, user)
            
            # Handle Session Expiry (Remember Me)
            if not request.session.get('remember_me'):
                request.session.set_expiry(0) # Close on browser close
            else:
                request.session.set_expiry(1209600) # 2 weeks
            
            # Clean up
            del request.session['pre_login_id']
            del request.session['login_otp']
            if 'remember_me' in request.session: del request.session['remember_me']
            
            # Loading Animation
            return render(request, 'account/loading.html')
        
        messages.error(request, "Invalid Code")
    return render(request, 'account/otp.html')

def logout_view(request): 
    logout(request)
    return redirect('login')

# Forgot Password Flow
def forgot_access_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email__iexact=email)
            otp = str(random.randint(100000, 999999))
            request.session['recovery_user_id'] = user.id
            request.session['recovery_otp'] = otp
            send_premium_otp(user, otp, "recover your account access")
            return redirect('recover_otp')
        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
    return render(request, 'account/forgot_access.html')

def recover_otp_view(request):
    if 'recovery_user_id' not in request.session: return redirect('login')
    if request.method == 'POST':
        if 'resend_code' in request.POST:
            new_otp = str(random.randint(100000, 999999))
            request.session['recovery_otp'] = new_otp
            try:
                user = User.objects.get(id=request.session['recovery_user_id'])
                send_premium_otp(user, new_otp, "recover account (Resend)")
                messages.success(request, "New code sent.")
            except: pass
            return redirect('recover_otp')
        if request.POST.get('otp_code') == request.session.get('recovery_otp'):
            request.session['recovery_verified'] = True
            return redirect('reset_access')
        else: messages.error(request, "Invalid Security Code")
    return render(request, 'account/recover_otp.html')

def reset_access_view(request):
    if not request.session.get('recovery_verified'): return redirect('login')
    user = User.objects.get(id=request.session['recovery_user_id'])
    
    if request.method == 'POST':
        new_pass = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        if new_pass == confirm:
            user.set_password(new_pass)
            user.save()
            del request.session['recovery_user_id']
            del request.session['recovery_otp']
            del request.session['recovery_verified']
            messages.success(request, "Access Restored. Please log in.")
            return redirect('login')
        else: messages.error(request, "Passwords do not match.")
    return render(request, 'account/reset_access.html', {'username': user.username})

# ==========================================
# 5. BANKING OPERATIONS
# ==========================================

@login_required(login_url='/login/')
def create_pin(request):
    if request.method == 'POST':
        pin = request.POST.get('pin')
        if len(pin) == 4 and pin.isdigit():
            request.user.account.transaction_pin = pin
            request.user.account.save()
            messages.success(request, "PIN Created")
            return redirect('transfer')
        messages.error(request, "Invalid PIN")
    return render(request, 'account/create_pin.html')

@login_required(login_url='/login/')
def transfer_money(request):
    account = request.user.account
    if not account.transaction_pin: return redirect('create_pin')
    popup_data = request.session.pop('txn_popup', None) 
    
    if request.method == 'POST':
        if 'forgot_pin' in request.POST:
            otp = str(random.randint(100000, 999999))
            request.session['reset_pin_otp'] = otp
            send_premium_otp(request.user, otp, "reset your PIN")
            return redirect('otp_verify')

        pin = request.POST.get('pin')
        amount = Decimal(request.POST.get('amount'))
        t_type = request.POST.get('type')
        
        # Internal Validation
        if t_type == 'internal':
            target_account_num = request.POST.get('account_number')
            if target_account_num == account.account_number:
                messages.error(request, "Cannot transfer money to yourself.")
                return redirect('transfer')
            if not Account.objects.filter(account_number=target_account_num).exists():
                messages.error(request, "Recipient account number not found.")
                return redirect('transfer')

        # PIN & Balance Check
        if pin != account.transaction_pin:
            account.pin_attempts += 1
            account.save()
            if account.pin_attempts >= 5:
                account.account_status = 'blocked'
                account.save()
                messages.error(request, "Account Blocked due to failed attempts.")
                return redirect('dashboard')
            else:
                messages.error(request, f"Incorrect PIN. {5-account.pin_attempts} attempts left.")
                return redirect('transfer')
        
        account.pin_attempts = 0
        account.save()

        if account.balance < amount:
            messages.error(request, "Insufficient Funds")
            return redirect('transfer')

        txn_data = {
            'type': t_type, 
            'amount': str(amount), 
            'account_number': request.POST.get('account_number'), 
            'routing': request.POST.get('routing_number'), 
            'bank_name': request.POST.get('bank_name'), 
            'note': request.POST.get('note') 
        }
        
        # High Value OTP Check
        if amount >= 1000:
            otp = str(random.randint(100000, 999999))
            request.session['txn_data'] = txn_data
            request.session['txn_otp'] = otp
            send_premium_otp(request.user, otp, f"authorize transfer of ${amount}")
            return redirect('transfer_otp')

        return execute_transfer(request, txn_data, amount)

    return render(request, 'account/transfer.html', {'popup_data': popup_data, 'account': account})

def execute_transfer(request, data, amount):
    sender = request.user.account
    sender.balance -= amount
    sender.save()
    
    receiver_user = None
    final_status = 'success'
    
    # Internal Credit Logic
    if data['type'] == 'internal':
        try:
            target_account = Account.objects.get(account_number=data['account_number'])
            target_account.balance += amount
            target_account.save()
            receiver_user = target_account.user
            Notification.objects.create(user=receiver_user, message=f"Credit Alert: You received ${amount} from {request.user.username}.")
            send_transaction_alert(receiver_user, amount, "Incoming Transfer", "Successful")
        except: pass
    
    if data['type'] == 'external':
        final_status = 'processing'
    
    Transaction.objects.create(
        sender=request.user, 
        receiver=receiver_user, 
        amount=amount, 
        transaction_type=data['type'], 
        status=final_status, 
        receiver_account_number=data.get('account_number'), 
        routing_number=data.get('routing'), 
        receiver_bank_name=data.get('bank_name'), 
        note=data.get('note')
    )
    
    send_transaction_alert(request.user, amount, data['type'], final_status)
    request.session['txn_popup'] = {
        'status': final_status, 
        'amount': str(amount), 
        'msg': 'Transfer ' + final_status.title()
    }
    return redirect('transfer')

@login_required(login_url='/login/')
def transfer_otp(request):
    if 'txn_data' not in request.session: return redirect('transfer')
    if request.method == 'POST':
        if 'resend_code' in request.POST:
             new_otp = str(random.randint(100000, 999999))
             request.session['txn_otp'] = new_otp
             send_premium_otp(request.user, new_otp, "authorize transaction")
             messages.success(request, "New code sent.")
             return redirect('transfer_otp')

        if request.POST.get('otp') == request.session.get('txn_otp'):
            data = request.session['txn_data']
            execute_transfer(request, data, Decimal(data['amount']))
            del request.session['txn_data']
            del request.session['txn_otp']
            return redirect('transfer')
        messages.error(request, "Invalid Code")
    return render(request, 'account/transfer_otp.html')

@login_required(login_url='/login/')
def dashboard(request):
    check_and_approve_transactions(request.user)
    try:
        user_account = request.user.account
        all_transactions = Transaction.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-date')
        
        # Pagination Logic
        if request.GET.get('view_all') == 'true':
            transactions = all_transactions
            is_viewing_all = True
        else:
            transactions = all_transactions[:5]
            is_viewing_all = False

        popup_data = request.session.pop('txn_popup', None) 
        
        card = CreditCard.objects.filter(user=request.user).first()
        active_loan = Loan.objects.filter(user=request.user, status='approved').first()
        
        today = timezone.now()
        m_txns = all_transactions.filter(date__month=today.month, date__year=today.year)
        money_in = m_txns.filter(receiver=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
        money_out = m_txns.filter(sender=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
        
        context = {
            'account': user_account, 
            'transactions': transactions, 
            'popup_data': popup_data, 
            'is_viewing_all': is_viewing_all, 
            'card': card,
            'active_loan': active_loan,
            'money_in': money_in,
            'money_out': money_out
        }
        return render(request, 'account/dashboard.html', context)
    except: return render(request, 'account/dashboard.html', {'error': 'No account found'})

@login_required(login_url='/login/')
def deposit_view(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        Transaction.objects.create(
            sender=None, receiver=request.user, amount=amount, 
            transaction_type='deposit', status='processing', 
            note="Mobile Check Deposit", 
            check_image=request.FILES.get('check_image'), 
            check_back_image=request.FILES.get('check_back_image')
        )
        request.session['txn_popup'] = {'status': 'processing', 'amount': str(amount), 'msg': 'Deposit Pending Review'}
        return redirect('dashboard')
    return render(request, 'account/deposit.html', {'account': request.user.account})

@login_required(login_url='/login/')
def pay_bills(request):
    account = request.user.account
    if not account.transaction_pin: return redirect('create_pin')
    popup_data = request.session.pop('txn_popup', None)
    
    if request.method == 'POST':
        if 'forgot_pin' in request.POST:
            otp = str(random.randint(100000, 999999))
            request.session['reset_pin_otp'] = otp
            send_premium_otp(request.user, otp, "reset your PIN")
            return redirect('otp_verify')
        
        pin = request.POST.get('pin')
        amount = Decimal(request.POST.get('amount'))
        
        if pin != account.transaction_pin:
            account.pin_attempts += 1; account.save()
            if account.pin_attempts >= 5:
                account.account_status = 'blocked'; account.save()
                messages.error(request, "Account Blocked")
                return redirect('dashboard')
            messages.error(request, "Incorrect PIN")
            return redirect('pay_bills')
            
        account.pin_attempts = 0; account.save()
        if account.balance < amount:
            messages.error(request, "Insufficient Funds")
        else:
            account.balance -= amount; account.save()
            Transaction.objects.create(sender=request.user, amount=amount, transaction_type='payment', status='success', note=f"Bill Pay: {request.POST.get('biller')}")
            send_transaction_alert(request.user, amount, 'Bill Payment', 'Success')
            request.session['txn_popup'] = {'status': 'success', 'amount': str(amount), 'msg': 'Bill Paid Successfully'}
            return redirect('pay_bills')
    return render(request, 'account/pay_bills.html', {'account': account, 'popup_data': popup_data})

@login_required(login_url='/login/')
def loans_view(request):
    loans = Loan.objects.filter(user=request.user).order_by('-date_applied')
    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] == 'repay':
            pin = request.POST.get('pin')
            if pin != request.user.account.transaction_pin:
                messages.error(request, "Incorrect PIN")
                return redirect('loans')

            loan_id = request.POST.get('loan_id')
            repay_amount = Decimal(request.POST.get('repay_amount'))
            loan = Loan.objects.get(id=loan_id, user=request.user)
            
            if request.user.account.balance >= repay_amount:
                request.user.account.balance -= repay_amount; request.user.account.save()
                loan.amount_paid += repay_amount
                if loan.amount_paid >= loan.total_repayment: loan.status = 'paid'
                loan.save()
                Transaction.objects.create(sender=request.user, amount=repay_amount, transaction_type='repayment', status='success', note=f"Loan Repay: {loan.purpose}")
                send_transaction_alert(request.user, repay_amount, 'Loan Repayment', 'Success')
                messages.success(request, "Repayment Successful")
            else:
                messages.error(request, "Insufficient Funds")
            return redirect('loans')
        else:
            amount = Decimal(request.POST.get('amount'))
            purpose = request.POST.get('purpose')
            term = int(request.POST.get('term'))
            interest = amount * Decimal('0.05')
            total = amount + interest
            
            Loan.objects.create(user=request.user, amount=amount, total_repayment=total, term_months=term, purpose=purpose)
            send_transaction_alert(request.user, amount, 'Loan Application', 'Pending Review')
            
            request.session['txn_popup'] = {'status': 'processing', 'amount': str(amount), 'msg': 'Loan Application Received'}
            return redirect('loans')
    return render(request, 'account/loans.html', {'loans': loans, 'account': request.user.account, 'popup_data': request.session.pop('txn_popup', None)})

@login_required(login_url='/login/')
def kyc_upload_view(request):
    if request.method == 'POST':
        a = request.user.account; a.id_card_front = request.FILES.get('id_front'); a.id_card_back = request.FILES.get('id_back'); a.kyc_submitted = True; a.save()
        messages.success(request, "Documents Submitted"); return redirect('profile')
    return render(request, 'account/kyc.html', {'account': request.user.account})

@login_required(login_url='/login/')
def card_detail(request):
    cards = CreditCard.objects.filter(user=request.user)
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'toggle_freeze':
            try: c = CreditCard.objects.get(id=request.POST.get('card_id'), user=request.user); c.is_frozen = not c.is_frozen; c.save(); return redirect('cards')
            except: pass
        elif action == 'apply_card':
            CreditCard.objects.create(user=request.user, card_number=f"4000{random.randint(100000000000, 999999999999)}", cvv=str(random.randint(100, 999)), expiry_date="12/28", card_style=request.POST.get('card_style'))
            messages.success(request, "Card Issued"); return redirect('cards')
    return render(request, 'account/cards.html', {'cards': cards, 'account': request.user.account})

@login_required(login_url='/login/')
def profile_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'upload_avatar' and request.FILES.get('profile_pic'):
            request.user.account.profile_pic = request.FILES['profile_pic']; request.user.account.save(); return redirect('profile')
        elif action == 'edit_profile':
            u = request.user; a = u.account
            email = request.POST.get('email'); phone = request.POST.get('phone'); addr = request.POST.get('address')
            if email: u.email = email; u.save()
            if phone: a.phone = phone; a.save()
            if addr: a.address = addr; a.save()
            messages.success(request, "Profile Updated"); return redirect('profile')
    return render(request, 'account/profile.html', {'account': request.user.account})

@login_required(login_url='/login/')
def transaction_detail(request, transaction_id):
    try: t = Transaction.objects.get(id=transaction_id); return render(request, 'account/transaction_detail.html', {'t': t, 'account': request.user.account})
    except: return redirect('dashboard')
@login_required(login_url='/login/')
def transaction_receipt(request, transaction_id): return render(request, 'account/receipt.html', {'transaction': Transaction.objects.get(id=transaction_id)})
@login_required(login_url='/login/')
def analytics_view(request):
    w = Transaction.objects.filter(sender=request.user, transaction_type='wire').aggregate(Sum('amount'))['amount__sum'] or 0
    t = Transaction.objects.filter(sender=request.user, transaction_type='transfer').aggregate(Sum('amount'))['amount__sum'] or 0
    i = Transaction.objects.filter(receiver=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    o = Transaction.objects.filter(sender=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'account/analytics.html', {'wire_total': w, 'transfer_total': t, 'money_in': i, 'money_out': o, 'account': request.user.account})
@login_required(login_url='/login/')
def support_view(request):
    if request.method == 'POST': SupportMessage.objects.create(user=request.user, message=request.POST.get('message')); return redirect('support')
    chat_history = SupportMessage.objects.filter(user=request.user).order_by('timestamp')
    return render(request, 'account/support.html', {'messages': chat_history, 'account': request.user.account})
@login_required(login_url='/login/')
def clear_notifications(request): Notification.objects.filter(user=request.user).delete(); return redirect(request.META.get('HTTP_REFERER'))
@login_required(login_url='/login/')
def delete_notification(request, notif_id): Notification.objects.filter(id=notif_id).delete(); return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/login/')
def documents_view(request):
    today = timezone.now(); dates = [(today - timedelta(days=30*i)).strftime("%B %Y") for i in range(12)]
    return render(request, 'account/documents.html', {'account': request.user.account, 'statements': dates})

@login_required(login_url='/login/')
def statement_view(request):
    date_str = request.GET.get('month') 
    try: date_obj = datetime.strptime(date_str, "%B %Y")
    except: date_obj = timezone.now()
    transactions = Transaction.objects.filter(Q(sender=request.user) | Q(receiver=request.user), date__year=date_obj.year, date__month=date_obj.month).order_by('-date')
    return render(request, 'account/statement_pdf.html', {'account': request.user.account, 'transactions': transactions, 'date': date_obj})

def custom_404(request, exception): return render(request, '404.html', status=404)
def custom_500(request): return render(request, '500.html', status=500)