from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # 既存のURL
    path('mypage/', views.MyPageView.as_view(), name='mypage'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('password/change/', views.password_change_view, name='password_change'),
    
    # Stripe決済関連URL
    path('subscription/plan/', views.SubscriptionPlanView.as_view(), name='subscription_plan'),
    path('subscription/create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('subscription/manage/', views.SubscriptionManageView.as_view(), name='subscription_manage'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # 決済完了・キャンセルページ
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/cancel/', views.PaymentCancelView.as_view(), name='payment_cancel'),
    
    # Stripe WebHook
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # カード管理機能
    path('card/manage/', views.CardManageView.as_view(), name='card_manage'),
    path('card/add/', views.CardAddView.as_view(), name='card_add'),
    path('card/change/', views.CardChangeView.as_view(), name='card_change'),
    path('billing/portal/', views.billing_portal, name='billing_portal'),
    
    # カード操作用URL
    path('card/set-default/', views.set_default_card, name='set_default_card'),
    path('card/remove/', views.remove_payment_method, name='remove_payment_method'),
]
