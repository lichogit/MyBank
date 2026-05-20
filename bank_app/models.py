from django.db import models

class Client(models.Model):
    CLIENT_TYPES = (
        ('INDIVIDUAL', 'Individual'),
        ('CORPORATE', 'Corporate'),
    )
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPES)
    
    # Individual fields
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    personal_id = models.CharField(max_length=20, blank=True, null=True, unique=True) # EGN
    
    # Corporate fields
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company_id = models.CharField(max_length=50, blank=True, null=True, unique=True) # EIK
    representative_name = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        if self.client_type == 'INDIVIDUAL':
            return f"{self.first_name} {self.last_name}"
        return self.company_name

class Account(models.Model):
    ACCOUNT_STATUS = (
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='accounts')
    iban = models.CharField(max_length=34, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=ACCOUNT_STATUS, default='ACTIVE')

    def __str__(self):
        return self.iban

class CreditType(models.Model):
    CREDIT_NAMES = (
        ('CONSUMER', 'Consumer Credit'),
        ('MORTGAGE', 'Mortgage Credit'),
    )
    name = models.CharField(max_length=50, choices=CREDIT_NAMES, unique=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2) 
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_period_months = models.IntegerField()

    def __str__(self):
        return self.get_name_display()

class Credit(models.Model):
    CREDIT_STATUS = (
        ('ACTIVE', 'Active'),
        ('PAID', 'Paid'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='credits')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='credits')
    credit_type = models.ForeignKey(CreditType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    period_months = models.IntegerField()
    status = models.CharField(max_length=10, choices=CREDIT_STATUS, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Credit {self.id} - {self.client} ({self.amount})"

    @property
    def repayment_account(self):
        if self.account:
            return self.account
        return self.client.accounts.filter(status='ACTIVE').first()

    @property
    def remaining_amount(self):
        return sum(inst.installment_amount for inst in self.installments.filter(is_paid=False))


class Installment(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='installments')
    month_number = models.IntegerField()
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    principal_part = models.DecimalField(max_digits=10, decimal_places=2)
    interest_part = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Month {self.month_number} for Credit {self.credit.id}"
