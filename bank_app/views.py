from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from django.core.exceptions import ValidationError

from .models import Client, Account, Credit, Installment, CreditType
from .forms import ClientForm, CreditForm
from . import services

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

def dashboard(request):
    clients_count = Client.objects.count()
    accounts_count = Account.objects.count()
    credits_count = Credit.objects.count()
    return render(request, 'bank_app/dashboard.html', {
        'clients_count': clients_count,
        'accounts_count': accounts_count,
        'credits_count': credits_count
    })

def client_list(request):
    clients = Client.objects.all()
    return render(request, 'bank_app/client_list.html', {'clients': clients})

def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            try:
                services.create_client(**form.cleaned_data)
                messages.success(request, 'Client created successfully.')
                return redirect('client_list')
            except ValidationError as e:
                messages.error(request, str(e.message))
    else:
        form = ClientForm()
    return render(request, 'bank_app/client_form.html', {'form': form})

def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    accounts = client.accounts.all()
    credits = client.credits.all()
    return render(request, 'bank_app/client_detail.html', {
        'client': client,
        'accounts': accounts,
        'credits': credits
    })

def account_create(request, client_id):
    if request.method == 'POST':
        try:
            services.create_account(client_id)
            messages.success(request, 'Account created successfully.')
        except Exception as e:
            messages.error(request, f'Error creating account: {e}')
    return redirect('client_detail', pk=client_id)

def account_deposit(request, account_id):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = Decimal(amount)
            account = get_object_or_404(Account, pk=account_id)
            if account.status != 'ACTIVE':
                raise ValidationError("Cannot deposit to a closed account.")
            account.balance += amount
            account.save()
            messages.success(request, f'Deposited {amount} successfully.')
            return redirect('client_detail', pk=account.client.id)
        except Exception as e:
            messages.error(request, f'Error depositing: {e.message if hasattr(e, "message") else str(e)}')
    return redirect('dashboard')

def account_close(request, account_id):
    if request.method == 'POST':
        account = get_object_or_404(Account, pk=account_id)
        try:
            services.close_account(account.id)
            messages.success(request, f'Account {account.iban} has been closed.')
            return redirect('client_detail', pk=account.client.id)
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
            return redirect('client_detail', pk=account.client.id)
    return redirect('dashboard')

def credit_create(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    active_accounts = client.accounts.filter(status='ACTIVE')
    if not active_accounts.exists():
        messages.error(request, 'The client must have at least one active bank account to receive a credit.')
        return redirect('client_detail', pk=client.id)

    if request.method == 'POST':
        form = CreditForm(request.POST, client=client)
        if form.is_valid():
            try:
                services.grant_credit(
                    client_id=client.id,
                    credit_type_id=form.cleaned_data['credit_type'].id,
                    amount=form.cleaned_data['amount'],
                    period_months=form.cleaned_data['period_months'],
                    account_id=form.cleaned_data['account'].id
                )
                messages.success(request, 'Credit granted and repayment plan generated.')
                return redirect('client_detail', pk=client.id)
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, "message") else str(e))
    else:
        form = CreditForm(client=client)
    return render(request, 'bank_app/credit_form.html', {'form': form, 'client': client})

def credit_detail(request, pk):
    credit = get_object_or_404(Credit, pk=pk)
    installments = credit.installments.all().order_by('month_number')
    return render(request, 'bank_app/credit_detail.html', {
        'credit': credit,
        'installments': installments
    })

def credit_pay_all(request, pk):
    if request.method == 'POST':
        credit = get_object_or_404(Credit, pk=pk)
        try:
            services.pay_all_installments(credit.id)
            messages.success(request, 'All remaining installments paid successfully.')
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        return redirect('credit_detail', pk=credit.id)
    return redirect('dashboard')

def installment_pay(request, pk):
    if request.method == 'POST':
        installment = get_object_or_404(Installment, pk=pk)
        try:
            services.pay_installment(installment.id)
            messages.success(request, 'Installment paid successfully.')
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        return redirect('credit_detail', pk=installment.credit.id)
    return redirect('dashboard')
