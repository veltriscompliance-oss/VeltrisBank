from django.contrib import admin
from django.utils.html import format_html
from .models import Account, Transaction, CreditCard, Notification, SupportMessage, Loan

# --- MANAGER QUICK ACTIONS ---
@admin.action(description='✅ Approve Selected Transactions')
def approve_transactions(modeladmin, request, queryset):
    for txn in queryset:
        if txn.status != 'success':
            txn.status = 'success'
            txn.save() # Triggers balance update signal

@admin.action(description='❌ Reject Selected Transactions')
def reject_transactions(modeladmin, request, queryset):
    queryset.update(status='failed', rejection_reason="Compliance Review Failed")

@admin.action(description='✅ Approve Selected Loans')
def approve_loans(modeladmin, request, queryset):
    for loan in queryset:
        if loan.status != 'approved':
            loan.status = 'approved'
            loan.save() # Triggers credit signal

@admin.action(description='🔍 Verify KYC Identity')
def verify_kyc(modeladmin, request, queryset):
    queryset.update(kyc_confirmed=True, account_status='active')


# --- PROFESSIONAL ADMIN DASHBOARDS ---

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    # FIXED: Replaced 'status_badge' with 'account_status' so it can be edited
    list_display = ('user_info', 'account_number', 'formatted_balance', 'account_status', 'kyc_badge', 'view_id_docs')
    list_filter = ('account_status', 'kyc_confirmed')
    search_fields = ('account_number', 'user__username', 'user__email', 'phone')
    list_editable = ('account_status',) 
    readonly_fields = ('account_number',)

    fieldsets = (
        ('Account Holder', {
            'fields': ('user', 'profile_pic', 'account_number')
        }),
        ('Financial Status', {
            'fields': ('balance', 'credit_score', 'account_status')
        }),
        ('Compliance & KYC', {
            'fields': ('kyc_submitted', 'kyc_confirmed', 'id_card_front', 'id_card_back', 'ssn', 'date_of_birth')
        }),
        ('Contact Details', {
            'fields': ('phone', 'address', 'city', 'zip_code')
        }),
        ('Security Settings', {
            'fields': ('transaction_pin', 'pin_attempts', 'email_alerts', 'hide_balance', 'dark_mode')
        }),
    )

    @admin.display(description='User')
    def user_info(self, obj):
        return obj.user.username

    @admin.display(description='Balance')
    def formatted_balance(self, obj):
        return f"${obj.balance:,.2f}"

    @admin.display(description='KYC Status')
    def kyc_badge(self, obj):
        if obj.kyc_confirmed:
            return format_html('<span style="color:green; font-weight:bold;">✔ Verified</span>')
        if obj.kyc_submitted:
            return format_html('<span style="color:orange; font-weight:bold;">⚠ Review Needed</span>')
        return format_html('<span style="color:gray;">❌ Not Submitted</span>')

    @admin.display(description='ID Documents')
    def view_id_docs(self, obj):
        links = []
        if obj.id_card_front: links.append(f'<a href="{obj.id_card_front.url}" target="_blank">Front</a>')
        if obj.id_card_back: links.append(f'<a href="{obj.id_card_back.url}" target="_blank">Back</a>')
        return format_html(" | ".join(links)) if links else "-"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # FIXED: Replaced 'status_badge' with 'status' and 'date_fmt' with 'date'
    list_display = ('transaction_ref', 'user_info', 'amount_fmt', 'type_badge', 'status', 'date', 'proof_link', 'rejection_reason')
    list_filter = ('status', 'transaction_type', 'date')
    search_fields = ('sender__username', 'receiver__username', 'amount', 'id')
    list_editable = ('status', 'date', 'rejection_reason') 
    actions = [approve_transactions, reject_transactions]
    date_hierarchy = 'date'

    fieldsets = (
        ('Transaction Info', {
            'fields': ('sender', 'receiver', 'amount', 'transaction_type', 'status', 'date')
        }),
        ('External Wire Details', {
            'fields': ('receiver_bank_name', 'receiver_account_number', 'routing_number', 'note'),
            'classes': ('collapse',) 
        }),
        ('Audit & Compliance', {
            'fields': ('check_image', 'check_back_image', 'rejection_reason')
        }),
    )

    @admin.display(description='Ref ID')
    def transaction_ref(self, obj):
        return f"TRX-{obj.id}"

    @admin.display(description='Flow')
    def user_info(self, obj):
        sender = obj.sender.username if obj.sender else "System"
        receiver = obj.receiver.username if obj.receiver else "External"
        return f"{sender} ➝ {receiver}"
    
    @admin.display(description='Amount')
    def amount_fmt(self, obj):
        return f"${obj.amount:,.2f}"

    @admin.display(description='Type')
    def type_badge(self, obj):
        return obj.transaction_type.replace('_', ' ').title()

    @admin.display(description='Proof')
    def proof_link(self, obj):
        if obj.check_image:
            return format_html('<a href="{}" target="_blank">View Check</a>', obj.check_image.url)
        return "-"


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    # FIXED: Replaced 'status_badge' with 'status'
    list_display = ('user', 'amount_fmt', 'purpose', 'status', 'date_applied')
    list_filter = ('status', 'date_applied')
    search_fields = ('user__username', 'amount')
    list_editable = ('status',)
    actions = [approve_loans]

    @admin.display(description='Amount')
    def amount_fmt(self, obj):
        return f"${obj.amount:,.2f}"


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'direction', 'timestamp')
    list_filter = ('is_admin_reply', 'timestamp')
    search_fields = ('user__username', 'message')
    readonly_fields = ('timestamp',)
    
    def message_preview(self, obj):
        return obj.message[:60] + "..." if len(obj.message) > 60 else obj.message
    
    def direction(self, obj):
        return "Admin ➝ User" if obj.is_admin_reply else "User ➝ Admin"

admin.site.register(CreditCard)
admin.site.register(Notification)