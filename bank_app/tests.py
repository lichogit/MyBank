from django.test import TestCase
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import Client, Account, CreditType, Credit, Installment
from .services import (
    create_client,
    generate_iban,
    calculate_annuity,
    grant_credit,
    pay_installment,
    pay_all_installments,
    close_account
)

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
        # Create a default active account for credit disbursement and payments
        self.account = Account.objects.create(
            client=self.client,
            iban='BG00MYBK11111111111111',
            balance=Decimal('2000.00'),
            status='ACTIVE'
        )

    def test_calculate_annuity(self):
        # 10000 at 5% for 12 months -> 856.07
        annuity = calculate_annuity(10000, 5.0, 12)
        self.assertAlmostEqual(float(annuity), 856.07, places=2)

    def test_grant_credit_valid(self):
        # Grant credit should disburse 10000 BGN to self.account
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12, self.account.id)
        self.assertEqual(credit.client, self.client)
        self.assertEqual(credit.amount, 10000)
        self.assertEqual(credit.installments.count(), 12)
        
        # Check first installment
        first_inst = credit.installments.first()
        self.assertAlmostEqual(float(first_inst.installment_amount), 862.96, places=1) # ~10000 at 6.5% for 12 months

        # Check account balance increased by 10000 
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('12000.00'))

    def test_grant_credit_exceeds_max_amount(self):
        with self.assertRaises(ValidationError):
            grant_credit(self.client.id, self.consumer_credit_type.id, 60000, 12, self.account.id)

    def test_grant_credit_exceeds_max_period(self):
        with self.assertRaises(ValidationError):
            grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 130, self.account.id)

    def test_pay_installment(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN', balance=Decimal('2000.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12, account.id)
        # account balance is now 12000.00 (disbursed 10000)
        first_inst = credit.installments.first()
        
        pay_installment(first_inst.id)
        
        first_inst.refresh_from_db()
        self.assertTrue(first_inst.is_paid)
        
        account.refresh_from_db()
        expected_balance = Decimal('12000.00') - first_inst.installment_amount
        self.assertAlmostEqual(account.balance, expected_balance)

    def test_pay_installment_insufficient_funds(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN2', balance=Decimal('100.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12, account.id)
        # account balance is now 10100.00. Set balance to 0 to simulate insufficient funds.
        account.balance = Decimal('0.00')
        account.save()

        first_inst = credit.installments.first()
        with self.assertRaises(ValidationError):
            pay_installment(first_inst.id)

    def test_pay_all_installments_success(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN_ALL', balance=Decimal('0.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 5000, 6, account.id)
        # account balance is now 5000.00
        total_repayment = sum(inst.installment_amount for inst in credit.installments.all())
        
        # Set balance to exactly total repayment + 100.00 
        account.balance = total_repayment + Decimal('100.00')
        account.save()
        
        pay_all_installments(credit.id)
        
        credit.refresh_from_db()
        self.assertEqual(credit.status, 'PAID')
        for inst in credit.installments.all():
            self.assertTrue(inst.is_paid)
            
        account.refresh_from_db()
        self.assertAlmostEqual(account.balance, Decimal('100.00'))

    def test_pay_all_installments_insufficient_funds(self):
        account = Account.objects.create(client=self.client, iban='TESTIBAN_ALL2', balance=Decimal('0.00'))
        credit = grant_credit(self.client.id, self.consumer_credit_type.id, 5000, 6, account.id)
        # Set balance to 0.00 
        account.balance = Decimal('0.00')
        account.save()
        
        with self.assertRaises(ValidationError):
            pay_all_installments(credit.id)

    def test_close_account_success(self):
        account = Account.objects.create(client=self.client, iban='CLOSEME', balance=Decimal('100.00'))
        close_account(account.id)
        account.refresh_from_db()
        self.assertEqual(account.status, 'CLOSED')

    def test_close_account_already_closed(self):
        account = Account.objects.create(client=self.client, iban='CLOSEME2', balance=Decimal('100.00'), status='CLOSED')
        with self.assertRaises(ValidationError):
            close_account(account.id)

    def test_deposit_to_closed_account(self):
        account = Account.objects.create(client=self.client, iban='CLOSEME_DEP', balance=Decimal('100.00'), status='CLOSED')
        from django.test import Client as TestClient
        test_client = TestClient()
        response = test_client.post(f'/accounts/{account.id}/deposit/', {'amount': '50.00'})
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('100.00'))

    def test_grant_credit_to_closed_account(self):
        account = Account.objects.create(client=self.client, iban='CLOSEME_CR', balance=Decimal('100.00'), status='CLOSED')
        with self.assertRaises(ValidationError):
            grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12, account.id)

    def test_close_account_with_active_loan(self):
        """Cannot close an account that has an active credit linked to it."""
        account = Account.objects.create(client=self.client, iban='LOAN_CLOSE_TEST', balance=Decimal('20000.00'))
        grant_credit(self.client.id, self.consumer_credit_type.id, 10000, 12, account.id)
        with self.assertRaises(ValidationError):
            close_account(account.id)

