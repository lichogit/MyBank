from django import forms
from .models import Client, Account, Credit, CreditType

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['client_type', 'first_name', 'last_name', 'personal_id', 'company_name', 'company_id', 'representative_name']

#ensure the input data is all correct before sending to the database
    def clean(self):
        cleaned_data = super().clean()
        client_type = cleaned_data.get('client_type')

        if client_type == 'INDIVIDUAL':
            first_name = cleaned_data.get('first_name')
            last_name = cleaned_data.get('last_name')
            personal_id = cleaned_data.get('personal_id')

            if not first_name:
                self.add_error('first_name', "First name is required for individual clients.")
            if not last_name:
                self.add_error('last_name', "Last name is required for individual clients.")
            
            if not personal_id:
                self.add_error('personal_id', "Personal ID is required for individual clients.")
            else:
                if not personal_id.isdigit():
                    self.add_error('personal_id', "Personal ID must contain only numbers.")
                if len(personal_id) != 10:
                    self.add_error('personal_id', f"Personal ID must be exactly 10 numbers long. You entered {len(personal_id)}.")

        elif client_type == 'CORPORATE':
            company_name = cleaned_data.get('company_name')
            company_id = cleaned_data.get('company_id')
            representative_name = cleaned_data.get('representative_name')

            if not company_name:
                self.add_error('company_name', "Company name is required for corporate clients.")
            
            if not company_id:
                self.add_error('company_id', "Company ID is required for corporate clients.")
            else:
                if not company_id.isdigit():
                    self.add_error('company_id', "Company ID must contain only numbers.")
                if len(company_id) != 9:
                    self.add_error('company_id', f"Company ID must be exactly 9 numbers long. You entered {len(company_id)}.")
            
            if not representative_name:
                self.add_error('representative_name', "Representative name is required for corporate clients.")

        return cleaned_data


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
