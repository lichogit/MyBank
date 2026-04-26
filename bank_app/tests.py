from django.test import TestCase
from decimal import Decimal
from .models import Client, Account, CreditType, Credit, Installment
from .services import create_client, generate_iban, calculate_annuity, grant_credit, pay_installment
from django.core.exceptions import ValidationError

class ServicesTestCase(TestCase):
    def setUp(self):
        self.consumer_credit_type = CreditType.objects.create(
            name='CONSUMER',
            interest_rate=Decimal('6.50'),
            max_amount=Decimal('50000.00'),
            max_period_months=120
        )
        self.client = Client.objects.create(
            client_type='INDIVIDUAL',
            first_name='Test',
            last_name='User',
            personal_id='1234567890'
        )

    def test_calculate_annuity(self):
        # 10000 at 5% for 12 months -> ~856.07
        annuity = calculate_annuity(10000, 5.0, 12)
        self.assertAlmostEqual(float(annuity), 856.07, places=2)

    def test_grant_credit_valid(self):
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12)
        self.assertEqual(credit.client, self.client)
        self.assertEqual(credit.amount, 10000)
        self.assertEqual(credit.installments.count(), 12)
        
        # Check first installment
        first_inst = credit.installments.first()
        self.assertAlmostEqual(float(first_inst.installment_amount), 862.96, places=1) # ~10000 at 6.5% for 12 months

    def test_grant_credit_exceeds_max_amount(self):
        with self.assertRaises(ValidationError):
            grant_credit(self.client.id, self.consumer_credit_type.id, 60000, 12)

    def test_grant_credit_exceeds_max_period(self):
        with self.assertRaises(ValidationError):
            grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 130)

    def test_pay_installment(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN', balance=Decimal('2000.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12)
        first_inst = credit.installments.first()
        
        pay_installment(first_inst.id)
        
        first_inst.refresh_from_db()
        self.assertTrue(first_inst.is_paid)
        
        account.refresh_from_db()
        expected_balance = Decimal('2000.00') - first_inst.installment_amount
        self.assertAlmostEqual(account.balance, expected_balance)

    def test_pay_installment_insufficient_funds(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN2', balance=Decimal('100.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12)
        first_inst = credit.installments.first()
        
        with self.assertRaises(ValidationError):
            pay_installment(first_inst.id)
