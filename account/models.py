from django.db import models
import uuid
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

# --- OPTIONS ---
ACCOUNT_STATUS = (('active', 'Active'), ('pending', 'Pending'), ('blocked', 'Blocked'))
TRANSACTION_TYPE = (('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('transfer', 'Transfer'), ('wire', 'Wire Transfer'), ('payment', 'Bill Payment'), ('loan', 'Loan Credit'), ('repayment', 'Loan Repayment'))
TRANSACTION_STATUS = (('success', 'Success'), ('pending', 'Pending'), ('failed', 'Failed'), ('processing', 'Processing'))
LOAN_STATUS = (('pending', 'Pending'), ('approved', 'Active'), ('rejected', 'Rejected'), ('paid', 'Paid Off'))

# --- MODELS ---
class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=12, unique=True, default=uuid.uuid4)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS, default='active')
    profile_pic = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    
    # PREFERENCES
    dark_mode = models.BooleanField(default=False)
    hide_balance = models.BooleanField(default=False)
    email_alerts = models.BooleanField(default=True)

    # SECURITY & KYC
    transaction_pin = models.CharField(max_length=4, blank=True, null=True)
    pin_attempts = models.IntegerField(default=0)
    credit_score = models.IntegerField(default=680)
    
    # PERSONAL INFO
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=10, blank=True) # Mapped from 'zipcode' form
    ssn = models.CharField(max_length=20, blank=True) 
    date_of_birth = models.DateField(null=True, blank=True) # Mapped from 'dob' form
    
    # IDENTITY DOCUMENTS
    id_card_front = models.ImageField(upload_to='kyc', blank=True, null=True)
    id_card_back = models.ImageField(upload_to='kyc', blank=True, null=True)
    
    kyc_submitted = models.BooleanField(default=False)
    kyc_confirmed = models.BooleanField(default=False)
    
    def __str__(self): return f"{self.user.username} - {self.account_number}"

class Loan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2) # Principal
    term_months = models.IntegerField(default=12)
    purpose = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='pending')
    date_applied = models.DateTimeField(auto_now_add=True)
    
    # Repayment Tracking
    total_repayment = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # Principal + Interest
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    def __str__(self): return f"{self.user.username} - ${self.amount} ({self.status})"
    
    # Template Helpers
    @property
    def remaining_amount(self):
        return self.total_repayment - self.amount_paid

    @property
    def progress(self):
        if self.total_repayment == 0: return 0
        return int((self.amount_paid / self.total_repayment) * 100)

class Transaction(models.Model):
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="sent_transactions", null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="received_transactions", null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE, default='transfer')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    date = models.DateTimeField(default=timezone.now)
    rejection_reason = models.CharField(max_length=255, blank=True, null=True)
    
    receiver_account_number = models.CharField(max_length=100, blank=True, null=True)
    receiver_bank_name = models.CharField(max_length=100, blank=True, null=True)
    routing_number = models.CharField(max_length=100, blank=True, null=True)
    note = models.CharField(max_length=100, blank=True, null=True)
    
    # CHECK IMAGES
    check_image = models.ImageField(upload_to='checks', blank=True, null=True)
    check_back_image = models.ImageField(upload_to='checks', blank=True, null=True)

    def __str__(self): return f"{self.transaction_type} - {self.amount} - {self.status}"

class CreditCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    card_number = models.CharField(max_length=16, unique=True)
    cvv = models.CharField(max_length=3)
    expiry_date = models.CharField(max_length=5)
    card_type = models.CharField(max_length=20, default='Visa')
    card_style = models.CharField(max_length=20, default='Virtual')
    is_frozen = models.BooleanField(default=False)
    def __str__(self): return f"{self.card_number}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
class SupportSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='active') # 'active' or 'closed'
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} - {self.user.username}"
class SupportMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(SupportSession, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_admin_reply = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

# --- SIGNALS ---
@receiver(pre_save, sender=Transaction)
def trigger_notification(sender, instance, **kwargs):
    if instance.pk: 
        try:
            old_txn = Transaction.objects.get(pk=instance.pk)
            # Balance Update on Approval (Deposit)
            if old_txn.status != 'success' and instance.status == 'success':
                if instance.transaction_type == 'deposit' and instance.receiver:
                    instance.receiver.account.balance += instance.amount
                    instance.receiver.account.save()
            # Notification Logic
            if old_txn.status != instance.status:
                target = instance.sender or instance.receiver
                if target: 
                    msg = f"Transaction Update: ${instance.amount} is now {instance.status.upper()}."
                    if instance.status == 'failed' and instance.rejection_reason: msg += f" Reason: {instance.rejection_reason}"
                    Notification.objects.create(user=target, message=msg)
        except: pass

@receiver(pre_save, sender=Loan)
def loan_approval_handler(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_loan = Loan.objects.get(pk=instance.pk)
            # Loan Approval Logic
            if old_loan.status != 'approved' and instance.status == 'approved':
                instance.user.account.balance += instance.amount; instance.user.account.save()
                
                # Interest Calculation (Default 5%) - Handled here if not set in view
                if instance.total_repayment == 0:
                    interest = instance.amount * Decimal('0.05')
                    instance.total_repayment = instance.amount + interest
                
                Transaction.objects.create(receiver=instance.user, amount=instance.amount, transaction_type='loan', status='success', note=f"Loan Approved: {instance.purpose}")
                Notification.objects.create(user=instance.user, message=f"Congratulations! Your loan of ${instance.amount} has been approved.")
        except: pass