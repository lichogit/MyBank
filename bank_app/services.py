import random
import string
from decimal import Decimal
from datetime import datetime
from .models import Client, Account, CreditType, Credit, Installment
from django.db import transaction
from django.core.exceptions import ValidationError

def create_client(client_type, **kwargs):
    if client_type == 'INDIVIDUAL':
        if not kwargs.get('first_name') or not kwargs.get('last_name') or not kwargs.get('personal_id'):
            raise ValidationError("Individual clients must have first_name, last_name, and personal_id")
    else:
        if not kwargs.get('company_name') or not kwargs.get('company_id') or not kwargs.get('representative_name'):
            raise ValidationError("Corporate clients must have company_name, company_id, and representative_name")

    return Client.objects.create(client_type=client_type, **kwargs)

def generate_iban():
    # IBAN generator for BG
    bank_code = "MYBK"
    acc_num = ''.join(random.choices(string.digits, k=14))
    return f"BG00{bank_code}{acc_num}"

def create_account(client_id):
    client = Client.objects.get(id=client_id)
    iban = generate_iban()
    # ensure uniqueness
    while Account.objects.filter(iban=iban).exists():
        iban = generate_iban()
    return Account.objects.create(client=client, iban=iban)

def calculate_annuity(principal, annual_interest_rate, months):
    """
    A = P * r * (1 + r)^n / ((1 + r)^n - 1)
    """
    P = Decimal(principal)

    # monthly rate
    
    r = Decimal(annual_interest_rate) / Decimal(100) / Decimal(12)
    n = months
    
    if r == 0:
        return P / n
    
    numerator = P * r * ((1 + r) ** n)
    denominator = ((1 + r) ** n) - 1
    
    return numerator / denominator

@transaction.atomic
def grant_credit(client_id, credit_type_id, amount, period_months, account_id):
    client = Client.objects.get(id=client_id)
    credit_type = CreditType.objects.get(id=credit_type_id)
    amount = Decimal(amount)
    account = Account.objects.get(id=account_id)
    
    if account.client != client:
        raise ValidationError("Selected account does not belong to the client")
    if account.status != 'ACTIVE':
        raise ValidationError("Selected account is not active")
    if amount > credit_type.max_amount:
        raise ValidationError(f"Amount exceeds the maximum allowed for {credit_type.get_name_display()} (max: {credit_type.max_amount:.2f} EUR)")
    if period_months > credit_type.max_period_months:
        raise ValidationError(f"Period exceeds maximum allowed for {credit_type.name}")
        
    credit = Credit.objects.create(
        client=client,
        account=account,
        credit_type=credit_type,
        amount=amount,
        period_months=period_months
    )
    
    # Generate repayment plan
    annuity = calculate_annuity(amount, credit_type.interest_rate, period_months)
    annuity = round(annuity, 2)
    
    remaining_principal = amount
    monthly_rate = Decimal(credit_type.interest_rate) / Decimal(100) / Decimal(12)
    
    for month in range(1, period_months + 1):
        if month == period_months:
            # Last month adjust to remaining
            interest = round(remaining_principal * monthly_rate, 2)
            principal = remaining_principal
            installment_amount = principal + interest
            remaining_principal = Decimal('0.00')
        else:
            interest = round(remaining_principal * monthly_rate, 2)
            principal = annuity - interest
            remaining_principal -= principal
            installment_amount = annuity
            
        Installment.objects.create(
            credit=credit,
            month_number=month,
            installment_amount=installment_amount,
            principal_part=principal,
            interest_part=interest,
            remaining_balance=remaining_principal
        )
        
    # Disburse funds directly into the selected account
    account.balance += amount
    account.save()
        
    return credit

@transaction.atomic
def pay_installment(installment_id):
    installment = Installment.objects.select_for_update().get(id=installment_id)
    if installment.is_paid:
        raise ValidationError("Installment is already paid")
        
    credit = installment.credit
    account = credit.repayment_account
    
    if not account:
        raise ValidationError("No active account to pay from")
        
    if account.status != 'ACTIVE':
        raise ValidationError("The associated account is not active")
        
    if account.balance < installment.installment_amount:
        raise ValidationError("Insufficient funds in account")
        
    account.balance -= installment.installment_amount
    account.save()
        
    installment.is_paid = True
    from django.utils import timezone
    installment.paid_at = timezone.now()
    installment.save()
    
    # Check if credit is fully paid
    unpaid = Installment.objects.filter(credit=installment.credit, is_paid=False).exists()
    if not unpaid:
        installment.credit.status = 'PAID'
        installment.credit.save()
        
    return installment

@transaction.atomic
def pay_all_installments(credit_id):
    credit = Credit.objects.get(id=credit_id)
    if credit.status == 'PAID':
        raise ValidationError("Credit is already fully paid")
        
    unpaid_installments = Installment.objects.select_for_update().filter(credit=credit, is_paid=False)
    if not unpaid_installments.exists():
        raise ValidationError("No unpaid installments found")
        
    total_amount = sum(inst.installment_amount for inst in unpaid_installments)
    
    account = credit.repayment_account
        
    if not account:
        raise ValidationError("No active account to pay from")
        
    if account.status != 'ACTIVE':
        raise ValidationError("The associated account is not active")
        
    if account.balance < total_amount:
        raise ValidationError(f"Insufficient funds in account (Required: {total_amount:.2f}, Available: {account.balance:.2f})")
        
    account.balance -= total_amount
    account.save()
    
    from django.utils import timezone
    now = timezone.now()
    for inst in unpaid_installments:
        inst.is_paid = True
        inst.paid_at = now
        inst.save()
        
    credit.status = 'PAID'
    credit.save()
    return credit

@transaction.atomic
def close_account(account_id):
    account = Account.objects.select_for_update().get(id=account_id)
    if account.status == 'CLOSED':
        raise ValidationError("Account is already closed")
    # Prevent closing if there are active  credits linked to this account
    active_credits = Credit.objects.filter(account=account, status='ACTIVE')
    if active_credits.exists():
        raise ValidationError("Cannot close this account — it has an active loan that must be fully repaid first.")
    account.status = 'CLOSED'
    account.save()
    return account
