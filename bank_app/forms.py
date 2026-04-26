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
