from django import forms
from .models import Client, Account, Credit, CreditType

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['client_type', 'first_name', 'last_name', 'personal_id', 'company_name', 'company_id', 'representative_name']

class CreditForm(forms.Form):
    credit_type = forms.ModelChoiceField(queryset=CreditType.objects.all())
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    period_months = forms.IntegerField(min_value=1)
    account = forms.ModelChoiceField(queryset=Account.objects.none())

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        if client:
            self.fields['account'].queryset = Account.objects.filter(client=client, status='ACTIVE')
            # Customize label display
            self.fields['account'].label_from_instance = lambda obj: f"{obj.iban} (Available: {obj.balance})"
