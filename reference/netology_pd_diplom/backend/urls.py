from django.urls import path
from backend.views import (
    BasketView, CategoryView, ContactView, OrderView, PartnerUpdate, 
    ProductInfoView, RegisterAccount, ConfirmAccount, LoginAccount, ShopView
    )
app_name = 'backend'

urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('basket', BasketView.as_view(), name='basket'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('categories/', CategoryView.as_view(), name='categories'),
    path('shops/', ShopView.as_view(), name='shops'),
    path('products', ProductInfoView.as_view(), name='products'),
    path('order/', OrderView.as_view(), name='order'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/contact/', ContactView.as_view(), name='user-contact-create-or-list'),
    path('user/contact/<int:pk>/', ContactView.as_view(), name='user-contact-update-or-delete'),
]
