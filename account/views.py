from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Account, Transaction, CreditCard, Notification, SupportMessage, Loan, SupportSession
from django.db.models import Q, Sum, Max, Count
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.contrib.auth.models import User
import uuid
import random
import threading
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator

# ==========================================
# 1. PREMIUM EMAIL ENGINE (THREADED)
# ==========================================

class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list):
        self.subject = subject
        self.recipient_list = recipient_list
        self.html_content = html_content
        threading.Thread.__init__(self)

    def run(self):
        try:
            msg = EmailMultiAlternatives(self.subject, strip_tags(self.html_content), settings.EMAIL_HOST_USER, self.recipient_list)
            msg.attach_alternative(self.html_content, "text/html")
            msg.send()
        except Exception as e:
            print(f"Email Sending Failed: {e}")

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
    EmailThread(subject, html_content, [user.email]).start()

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
    EmailThread(subject, html_content, [user.email]).start()


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def is_account_blocked(user):
    return hasattr(user, 'account') and user.account.account_status == 'blocked'

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
    if request.method == 'POST' and request.POST.get('action') == 'update_profile':
        user = request.user; account = user.account
        user.email = request.POST.get('email')
        account.phone = request.POST.get('phone')
        account.address = request.POST.get('address')
        account.city = request.POST.get('city')
        account.zip_code = request.POST.get('zip_code')
        user.save(); account.save()
        messages.success(request, "Profile Settings Updated Successfully")
        return redirect('settings')
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
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Initialize context
    form_data = {}
    field_errors = {}
    active_tab = 0 # Default to Step 1

    if request.method == 'POST':
        # Capture all submitted data to return it if validation fails
        form_data = request.POST.dict()
        
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        phone = request.POST.get('phone')

        # --- VALIDATION LOGIC ---
        has_error = False

        # 1. Password Match (Step 4 -> Index 3)
        if password != confirm:
            field_errors['password'] = "Passwords do not match"
            field_errors['confirm_password'] = "Passwords do not match"
            active_tab = 3 
            has_error = True

        # 2. Username Check (Step 4 -> Index 3)
        elif User.objects.filter(username=username).exists():
            field_errors['username'] = "This username is already taken"
            active_tab = 3
            has_error = True
        
        # 3. Email Check (Step 2 -> Index 1)
        elif User.objects.filter(email=email).exists():
            field_errors['email'] = "This email is already registered"
            active_tab = 1
            has_error = True
            
        # 4. Phone Length Check (Step 2 -> Index 1)
        # Assuming DB limit is 15. Form has maxlength, but good to double check.
        elif len(phone) > 15:
            field_errors['phone'] = "Phone number is too long"
            active_tab = 1
            has_error = True

        if has_error:
            # Return page with data and errors
            return render(request, 'account/register.html', {
                'form_data': form_data, 
                'field_errors': field_errors,
                'active_tab': active_tab
            })

        # --- CREATION LOGIC (If no errors) ---
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.save()

                dob = request.POST.get('dob')
                if not dob: dob = None 

                # Clean phone number just in case
                phone_clean = phone.replace(' ', '').replace('-', '')[:15]

                Account.objects.create(
                    user=user,
                    balance=Decimal('0.00'),
                    account_status='active',
                    account_number=str(uuid.uuid4().int)[:10],
                    phone=phone_clean,
                    address=request.POST.get('address', ''),
                    city=request.POST.get('city', ''),
                    zip_code=request.POST.get('zipcode', ''),
                    date_of_birth=dob,
                    ssn=request.POST.get('ssn', ''),
                    kyc_submitted=True,
                    kyc_confirmed=False
                )
            
            messages.success(request, "Registration successful! Please sign in.")
            return redirect('login')

        except Exception as e:
            print(f"Registration Error: {e}")
            messages.error(request, "An internal error occurred. Please try again.")
            # Default to Step 1 on crash
            return render(request, 'account/register.html', {'form_data': form_data})

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
        if 'resend_code' in request.POST:
            new_otp = str(random.randint(100000, 999999))
            request.session['login_otp'] = new_otp
            try:
                user = User.objects.get(id=request.session['pre_login_id'])
                send_premium_otp(user, new_otp, "log in (Resend)")
                messages.success(request, "New code sent.")
            except: pass
            return redirect('otp_verify')

        if request.POST.get('otp_code') == request.session.get('login_otp'):
            user = User.objects.get(id=request.session['pre_login_id'])
            login(request, user)
            
            if not request.session.get('remember_me'):
                request.session.set_expiry(0) 
            else:
                request.session.set_expiry(1209600)
            
            del request.session['pre_login_id']
            del request.session['login_otp']
            if 'remember_me' in request.session: del request.session['remember_me']
            
            return render(request, 'account/loading.html')
        
        messages.error(request, "Invalid Code")
    return render(request, 'account/otp.html')

def logout_view(request): 
    logout(request)
    return redirect('login')

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

# --- API FOR TRANSFER LOOKUP ---
@login_required(login_url='/login/')
def search_account(request):
    acc_num = request.GET.get('account_number')
    
    if not acc_num:
        return JsonResponse({'found': False, 'message': 'Enter account number'})

    try:
        target = Account.objects.get(account_number=acc_num)
        
        # Prevent transferring to self
        if target.user == request.user:
            return JsonResponse({'found': False, 'message': 'Cannot transfer to yourself'})
            
        return JsonResponse({
            'found': True, 
            'name': f"{target.user.first_name} {target.user.last_name}"
        })
        
    except Account.DoesNotExist:
        return JsonResponse({'found': False, 'message': 'Account not found'})

# -------------------------------

@login_required(login_url='/login/')
def transfer_money(request):
    if is_account_blocked(request.user):
        return redirect('/dashboard/?restricted=true')
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
        # --- FIX: TRANSLATE FORM TYPE TO DATABASE TYPE ---
        if t_type == 'external':
            final_type = 'wire'       # Save as Wire Transfer
        else:
            final_type = 'transfer'   # Save as Internal Transfer
        
        if t_type == 'internal':
            target_account_num = request.POST.get('account_number')
            if target_account_num == account.account_number:
                messages.error(request, "Cannot transfer money to yourself.")
                return redirect('transfer')
            if not Account.objects.filter(account_number=target_account_num).exists():
                messages.error(request, "Recipient account number not found.")
                return redirect('transfer')

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
            'type': final_type, 
            'amount': str(amount), 
            'account_number': request.POST.get('account_number'), 
            'routing': request.POST.get('routing_number'), 
            'bank_name': request.POST.get('bank_name'), 
            'note': request.POST.get('note') 
        }
        
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
    
    # 1. Determine Status: 'processing' if Wire OR High Value (>= 1000)
    if data['type'] == 'wire' or amount >= 1000:
        status = 'processing'
    else:
        status = 'success'
    
    receiver = None
    
    # 2. Handle Internal Transfer Logic
    if data['type'] == 'transfer': 
        try:
            target = Account.objects.get(account_number=data['account_number'])
            receiver = target.user
            
            # CRITICAL: Only credit receiver immediately if status is SUCCESS
            # If processing, the background task will credit them later
            if status == 'success':
                target.balance += amount
                target.save()
                Notification.objects.create(user=receiver, message=f"Credit Alert: Received ${amount} from {request.user.username}.")
                send_transaction_alert(receiver, amount, "Incoming Transfer", "Successful")
        except: pass

    # 3. Create Transaction Record
    Transaction.objects.create(
        sender=request.user, 
        receiver=receiver, 
        amount=amount,
        transaction_type=data['type'], 
        status=status, 
        receiver_account_number=data.get('account_number'), 
        routing_number=data.get('routing'), 
        receiver_bank_name=data.get('bank_name'), 
        note=data.get('note')
    )
    
    # 4. Send Sender Alert
    send_transaction_alert(request.user, amount, data['type'], status)
    
    # 5. Set Popup Message
    if status == 'success':
        msg_text = "Your transfer has been completed."
    else:
        msg_text = "Transaction is currently under review."

    request.session['txn_popup'] = {
        'status': status, 
        'amount': str(amount), 
        'msg': msg_text
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
        restricted = request.GET.get('restricted') == 'true'
        all_transactions = Transaction.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-date')
        
        # Pagination
        if request.GET.get('view_all') == 'true':
            transactions = all_transactions
            is_viewing_all = True
        else:
            transactions = all_transactions[:5]
            is_viewing_all = False

        popup_data = request.session.pop('txn_popup', None) 
        
        # Widgets Data
        card = CreditCard.objects.filter(user=request.user).first()
        active_loan = Loan.objects.filter(user=request.user, status='approved').first()
        
        # Monthly Stats
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
            'money_out': money_out,
            'restricted_attempt': restricted,
        }
        return render(request, 'account/dashboard.html', context)
    except: return render(request, 'account/dashboard.html', {'error': 'No account found'})

@login_required(login_url='/login/')
def deposit_view(request):
    if is_account_blocked(request.user):
        return redirect('/dashboard/?restricted=true')
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
    if is_account_blocked(request.user):
        return redirect('/dashboard/?restricted=true')
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

# --- LOANS ---
@login_required(login_url='/login/')
def loans_view(request):
    if is_account_blocked(request.user):
        return redirect('/dashboard/?restricted=true')
    loans = Loan.objects.filter(user=request.user).order_by('-date_applied')
    if request.method == 'POST':
        # Repayment Logic
        if 'action' in request.POST and request.POST['action'] == 'repay':
            pin = request.POST.get('pin')
            if pin != request.user.account.transaction_pin:
                messages.error(request, "Incorrect PIN")
                return redirect('loans')

            loan_id = request.POST.get('loan_id')
            repay_amount = Decimal(request.POST.get('repay_amount'))
            loan = Loan.objects.get(id=loan_id, user=request.user)
            
            if request.user.account.balance >= repay_amount:
                request.user.account.balance -= repay_amount
                request.user.account.save()
                
                loan.amount_paid += repay_amount
                if loan.amount_paid >= loan.total_repayment: loan.status = 'paid'
                loan.save()
                
                Transaction.objects.create(sender=request.user, amount=repay_amount, transaction_type='repayment', status='success', note=f"Loan Repayment: {loan.purpose}")
                send_transaction_alert(request.user, repay_amount, 'Loan Repayment', 'Success')
                messages.success(request, "Repayment Successful")
            else:
                messages.error(request, "Insufficient Funds")
            return redirect('loans')
        
        # Application Logic
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

# --- OTHER VIEWS ---
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
    # Your existing calculations
    w = Transaction.objects.filter(sender=request.user, transaction_type='wire').aggregate(Sum('amount'))['amount__sum'] or 0
    t = Transaction.objects.filter(sender=request.user, transaction_type='transfer').aggregate(Sum('amount'))['amount__sum'] or 0
    i = Transaction.objects.filter(receiver=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    o = Transaction.objects.filter(sender=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # The fix is adding 'gemini_api_key' to this dictionary below:
    return render(request, 'account/analytics.html', {
        'wire_total': w, 
        'transfer_total': t, 
        'money_in': i, 
        'money_out': o, 
        'account': request.user.account,
        'gemini_api_key': settings.GEMINI_API_KEY # <--- THIS WAS MISSING
    })

@login_required(login_url='/login/')
def support_view(request):
    # 1. Manage Session
    session = SupportSession.objects.filter(user=request.user, status='active').last()
    
    # Check Timeout (15 minutes)
    if session:
        time_since_activity = timezone.now() - session.last_activity
        if time_since_activity > timedelta(minutes=15):
            session.status = 'closed'
            session.save()
            session = None # Force creation of a new one below

    # Create new session if none exists
    if not session:
        session = SupportSession.objects.create(user=request.user)

    # 2. Handle New Messages
    if request.method == 'POST':
        message_text = request.POST.get('message')
        is_bot = request.POST.get('is_bot') == 'true'
        
        new_msg = None
        if message_text:
            new_msg = SupportMessage.objects.create(
                user=request.user, 
                session=session,
                message=message_text,
                is_admin_reply=is_bot
            )
            # Explicitly update the heartbeat so session doesn't die while typing
            session.last_activity = timezone.now()
            session.save() 
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'saved', 'id': new_msg.id if new_msg else 0})
            
        return redirect('support')
    
    # 3. Load History
    messages_list = SupportMessage.objects.filter(session=session).order_by('timestamp')

    # 4. FETCH SMART CONTEXT FOR AI
    recent_txns = Transaction.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-date')[:5]
    
    txn_context = ""
    if not recent_txns:
        txn_context = "No recent transactions."
    
    for t in recent_txns:
        date_str = t.date.strftime('%b %d')
        
        # Smart formatting: Add +/- signs so AI understands money flow
        if t.sender == request.user:
            # Money Leaving (Debit)
            amount_display = f"-${t.amount:,.2f}"
            if t.receiver:
                desc = f"Sent to {t.receiver.first_name} {t.receiver.last_name}"
            elif t.receiver_bank_name:
                desc = f"Wire to {t.receiver_bank_name}"
            else:
                desc = f"Payment: {t.note}" 
        else:
            # Money Coming In (Credit)
            amount_display = f"+${t.amount:,.2f}"
            if t.sender:
                desc = f"Received from {t.sender.first_name} {t.sender.last_name}"
            else:
                desc = "Mobile Deposit"

        # Format: "Oct 24: -$50.00 (Netflix) | Status: Success"
        txn_context += f"• {date_str}: {amount_display} ({desc}) | Status: {t.status}\n"

    return render(request, 'account/support.html', {
        'messages': messages_list, 
        'account': request.user.account, 
        'gemini_api_key': settings.GEMINI_API_KEY,
        'active_session': session,
        'transaction_context': txn_context # Passes the smart list to the template
    })

@login_required(login_url='/login/')
def get_messages_api(request):
    # 1. Get active session
    session = SupportSession.objects.filter(user=request.user, status='active').last()
    if not session:
        return JsonResponse({'messages': []})

    # 2. Fetch new messages ONLY from the active session
    last_id = request.GET.get('last_id', 0)
    new_msgs = SupportMessage.objects.filter(
        user=request.user, 
        session=session,
        id__gt=last_id
    ).order_by('timestamp')
    
    data = [{
        'id': m.id,
        'message': m.message,
        'is_admin': m.is_admin_reply,
        'time': m.timestamp.strftime('%H:%M')
    } for m in new_msgs]
    
    return JsonResponse({'messages': data})

@login_required(login_url='/login/')
def clear_notifications(request): Notification.objects.filter(user=request.user).delete(); return redirect(request.META.get('HTTP_REFERER'))
@login_required(login_url='/login/')
def delete_notification(request, notif_id): Notification.objects.filter(id=notif_id).delete(); return redirect(request.META.get('HTTP_REFERER'))

# --- DOCUMENTS ---
@login_required(login_url='/login/')
def documents_view(request):
    # This queries the DB for distinct months where activity actually occurred
    txn_dates = Transaction.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).dates('date', 'month', order='DESC')
    
    return render(request, 'account/documents.html', {'account': request.user.account, 'txn_dates': txn_dates})

@login_required(login_url='/login/')
def history_view(request):
    """Renders the main transaction history page shell."""
    return render(request, 'account/history.html', {'account': request.user.account})

@login_required(login_url='/login/')
def api_transaction_history(request):
    """
    JSON API for filtering, searching, and paginating transactions.
    Called by JavaScript on the history page.
    """
    user = request.user
    query = request.GET.get('q', '').strip()
    txn_type = request.GET.get('type', 'all')
    date_range = request.GET.get('date', 'all')
    page_number = request.GET.get('page', 1)

    # 1. Base Query
    txns = Transaction.objects.filter(Q(sender=user) | Q(receiver=user)).order_by('-date')

    # 2. Search Filter (Reference, Amount, Note)
    if query:
        txns = txns.filter(
            Q(transaction_id__icontains=query) |
            Q(amount__icontains=query) |
            Q(note__icontains=query) |
            Q(receiver_bank_name__icontains=query)
        )

    # 3. Type Filter
    if txn_type == 'credit':
        txns = txns.filter(receiver=user)
    elif txn_type == 'debit':
        txns = txns.filter(sender=user)
    
    # 4. Date Filter (Simple presets)
    today = timezone.now().date()
    if date_range == '7days':
        start_date = today - timedelta(days=7)
        txns = txns.filter(date__date__gte=start_date)
    elif date_range == '30days':
        start_date = today - timedelta(days=30)
        txns = txns.filter(date__date__gte=start_date)

    # 5. Pagination (20 items per load)
    paginator = Paginator(txns, 20)
    page_obj = paginator.get_page(page_number)

    # 6. Serialize Data
    data = []
    for t in page_obj:
        is_credit = t.receiver == user
        
        # --- LOGIC: DETERMINE HEADING (NAME vs NOTE) ---
        if is_credit:
            # Money IN: Show Sender Name
            if t.sender:
                display_title = f"{t.sender.first_name} {t.sender.last_name}"
            else:
                display_title = "Cash Deposit" 
        else:
            # Money OUT: Show Receiver Name or Bank
            if t.receiver:
                display_title = f"{t.receiver.first_name} {t.receiver.last_name}"
            elif t.receiver_bank_name:
                display_title = t.receiver_bank_name
            else:
                display_title = "External Payment"

        # Fallback if names are empty
        if not display_title.strip():
             display_title = t.note or "Transaction"

        data.append({
            'id': t.id,
            'amount': f"{t.amount:,.2f}",
            'type': t.transaction_type.title(),
            'status': t.status,
            'date': t.date.strftime('%b %d, %Y'),
            'time': t.date.strftime('%H:%M'),
            'is_credit': is_credit,
            'note': display_title, # <--- THIS IS THE FIX. We put the Name here.
            'reference': f"#{str(t.id).zfill(8)}", 
            'icon_class': 'icon-in' if is_credit else 'icon-out'
        })

    return JsonResponse({
        'transactions': data,
        'has_next': page_obj.has_next()
    })

@login_required(login_url='/login/')
def statement_view(request):
    date_str = request.GET.get('month') # Expects format: "YYYY-MM-DD"
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        month = date_obj.month
        year = date_obj.year
    except:
        # Fallback to current month if date is missing/invalid
        now = timezone.now()
        month, year = now.month, now.year
        date_obj = now

    # Filter transactions for that specific month
    transactions = Transaction.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        date__year=year, 
        date__month=month
    ).order_by('date') # Statements are usually chronological

    # Calculate Totals for the PDF Header
    total_in = transactions.filter(receiver=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    total_out = transactions.filter(sender=request.user).aggregate(Sum('amount'))['amount__sum'] or 0

    start_of_month = date_obj.replace(day=1)
    
    history_in = Transaction.objects.filter(receiver=request.user, date__lt=start_of_month).aggregate(Sum('amount'))['amount__sum'] or 0
    history_out = Transaction.objects.filter(sender=request.user, date__lt=start_of_month).aggregate(Sum('amount'))['amount__sum'] or 0
    
    beginning_balance = history_in - history_out
    
    return render(request, 'account/statement_pdf.html', {
        'account': request.user.account,
        'transactions': transactions,
        'date': date_obj,
        'total_in': total_in,
        'total_out': total_out,
        'beginning_balance': beginning_balance
    })

def is_staff(user):
    return user.is_staff or user.is_superuser

# ==========================================
# VELTRIS OPS COMMAND CENTER (FINAL SAFE VERSION)
# ==========================================

def is_staff(user):
    return user.is_staff or user.is_superuser

# 1. THE DASHBOARD SHELL
@user_passes_test(is_staff, login_url='/admin/login/')
def admin_dashboard(request):
    """Renders the main 3-panel layout."""
    return render(request, 'account/admin_dashboard.html')

# 2. THE QUEUE FETCHER (Left Panel)
@user_passes_test(is_staff)
def admin_fetch_queue(request):
    """Returns a list of all active support sessions."""
    active_sessions = SupportSession.objects.filter(status='active').order_by('-last_activity')
    
    data = []
    for s in active_sessions:
        # Check if the user is currently blocked (Safe check)
        is_blocked = False
        avatar_url = None
        try:
            if hasattr(s.user, 'account'):
                is_blocked = s.user.account.account_status == 'blocked'
                if s.user.account.profile_pic:
                    avatar_url = s.user.account.profile_pic.url
        except: pass

        # Count unread messages (Messages from User that Admin hasn't seen)
        last_msg = SupportMessage.objects.filter(session=s).last()
        preview = last_msg.message[:30] + "..." if last_msg else "New Session"
        is_user_waiting = last_msg and not last_msg.is_admin_reply

        data.append({
            'session_id': s.id,
            'user_id': s.user.id,
            'username': s.user.username,
            'full_name': f"{s.user.first_name} {s.user.last_name}",
            'avatar_url': avatar_url,
            'preview': preview,
            'timestamp': s.last_activity.strftime('%H:%M'),
            'is_blocked': is_blocked,
            'is_waiting': is_user_waiting,
        })
    
    return JsonResponse({'queue': data})

# 3. THE CHAT & GOD MODE FETCHER (Middle & Right Panel)
@user_passes_test(is_staff)
def admin_chat_data(request, session_id):
    """Fetches chat history AND User Financial Context."""
    session = get_object_or_404(SupportSession, id=session_id)
    user = session.user
    
    # SAFE ACCOUNT ACCESS
    balance = "0.00"
    acc_num = "N/A"
    currency = "USD"
    status = "Active"
    risk_score = 0
    
    try:
        if hasattr(user, 'account'):
            account = user.account
            balance = f"{account.balance:,.2f}"
            acc_num = account.account_number
            currency = account.currency
            status = account.account_status
            risk_score = 85
    except:
        status = "No Profile"

    # Get Chat History
    messages = SupportMessage.objects.filter(session=session).order_by('timestamp')
    chat_data = [{
        'id': m.id,
        'sender': 'admin' if m.is_admin_reply else 'user',
        'text': m.message,
        'time': m.timestamp.strftime('%H:%M')
    } for m in messages]

    # Context Data
    context_data = {
        'full_name': f"{user.first_name} {user.last_name}",
        'email': user.email,
        'account_number': acc_num,
        'balance': balance,
        'currency': currency,
        'status': status,
        'risk_score': risk_score, 
        'joined': user.date_joined.strftime('%b %Y')
    }

    return JsonResponse({
        'chat': chat_data,
        'context': context_data
    })

# 4. THE REPLY SENDER
@user_passes_test(is_staff)
def admin_reply(request):
    """Saves the Admin's message to the database."""
    if request.method == "POST":
        session_id = request.POST.get('session_id')
        message = request.POST.get('message')
        
        session = get_object_or_404(SupportSession, id=session_id)
        
        SupportMessage.objects.create(
            user=session.user,
            session=session,
            message=message,
            is_admin_reply=True
        )
        
        session.last_activity = timezone.now()
        session.save()
        
        return JsonResponse({'status': 'sent'})
    
    return JsonResponse({'status': 'error'}, status=400)

# 5. ADMIN ACTIONS (FREEZE / CLOSE)
@user_passes_test(is_staff)
def admin_action(request):
    """Handles Freeze/Unfreeze and Close Ticket actions."""
    if request.method == "POST":
        session_id = request.POST.get('session_id')
        action = request.POST.get('action') 
        
        session = get_object_or_404(SupportSession, id=session_id)
        user = session.user
        
        if action == 'freeze':
            # Toggle Freeze Status
            if hasattr(user, 'account'):
                acc = user.account
                if acc.account_status == 'blocked':
                    acc.account_status = 'active'
                    status_msg = "Account Unfrozen"
                else:
                    acc.account_status = 'blocked'
                    status_msg = "Account Frozen"
                acc.save()
                
                # System Log
                SupportMessage.objects.create(
                    user=user, session=session,
                    message=f"SYSTEM ALERT: {status_msg} by Admin.",
                    is_admin_reply=True
                )
                return JsonResponse({'status': 'success', 'new_state': acc.account_status})

        elif action == 'close':
            session.status = 'closed'
            session.save()
            return JsonResponse({'status': 'closed'})
            
    return JsonResponse({'status': 'error'}, status=400)

# 6. INJECT FUNDS (SIMULATOR)
@user_passes_test(is_staff)
def admin_simulate_transfer(request):
    """Allows Admin to simulate an incoming transfer from an external bank."""
    if request.method == "POST":
        session_id = request.POST.get('session_id')
        amount_str = request.POST.get('amount')
        bank_name = request.POST.get('bank_name')
        sender_name = request.POST.get('sender_name')
        
        try:
            session = get_object_or_404(SupportSession, id=session_id)
            user = session.user
            amount = Decimal(amount_str)
            
            # Credit
            user.account.balance += amount
            user.account.save()
            
            # Transaction Record
            Transaction.objects.create(
                sender=None, 
                receiver=user,
                amount=amount,
                transaction_type='wire', 
                status='success',
                note=f"Incoming Wire: {bank_name} - {sender_name}",
                receiver_bank_name=bank_name
            )
            
            # Notification (App)
            Notification.objects.create(
                user=user, 
                message=f"Credit Alert: You received ${amount:,.2f} from {sender_name} ({bank_name})."
            )

            # Email Alert (Simulation)
            send_transaction_alert(user, amount, f"Transfer from {bank_name}", "Success")

            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error'}, status=400)

def create_admin_backdoor(request):
    try:
        # Check if 'admin' exists to avoid crash
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            return HttpResponse("<h1>Success!</h1><p>User: <strong>admin</strong><br>Pass: <strong>admin123</strong></p>")
        else:
            return HttpResponse("<h1>Admin already exists.</h1>")
    except Exception as e:
        return HttpResponse(f"Error: {e}")
    
# --- ERROR HANDLERS ---
def custom_404(request, exception): return render(request, 'account/404.html', status=404)
def custom_500(request): return render(request, 'account/500.html', status=500)