from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('order_complete/', views.order_complete, name='order_complete'),
]