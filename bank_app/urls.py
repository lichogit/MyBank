from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('clients/', views.client_list, name='client_list'),
    path('clients/create/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:client_id>/accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:account_id>/deposit/', views.account_deposit, name='account_deposit'),
    path('clients/<int:client_id>/credits/create/', views.credit_create, name='credit_create'),
    path('credits/<int:pk>/', views.credit_detail, name='credit_detail'),
    path('installments/<int:pk>/pay/', views.installment_pay, name='installment_pay'),
]
