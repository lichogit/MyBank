import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybank_core.settings')
django.setup()

from bank_app.models import CreditType

def seed():
    CreditType.objects.get_or_create(name='CONSUMER', defaults={'interest_rate': 6.5, 'max_amount': 50000, 'max_period_months': 120})
    CreditType.objects.get_or_create(name='MORTGAGE', defaults={'interest_rate': 3.5, 'max_amount': 500000, 'max_period_months': 360})
    print("Database seeded with CreditTypes.")

if __name__ == '__main__':
    seed()
