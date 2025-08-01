from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    is_premium = models.BooleanField(default=False)
    
    # プロフィール情報
    postal_code = models.CharField(max_length=8, blank=True, null=True, verbose_name='郵便番号')
    address = models.TextField(blank=True, null=True, verbose_name='住所')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='電話番号')
    
    # Stripe関連
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email
    
    def get_subscription(self):
        # 現在のサブスクリプションを取得
        return Subscription.objects.filter(user=self, status='active').first()


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'アクティブ'),
        ('canceled', 'キャンセル済み'),
        ('past_due', '支払い遅延'),
        ('unpaid', '未払い'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_price_id = models.CharField(max_length=255)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.status}"
    
    @property
    def days_until_renewal(self):
        # 更新まであと何日か
        if self.current_period_end > timezone.now():
            return (self.current_period_end - timezone.now()).days
        return 0
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # ユーザーのプレミアム状態を更新
        if self.status == 'active' and self.current_period_end > timezone.now():
            self.user.is_premium = True
        else:
            self.user.is_premium = False
        
        self.user.stripe_customer_id = self.stripe_customer_id
        self.user.stripe_subscription_id = self.stripe_subscription_id
        self.user.save()


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ('succeeded', '成功'),
        ('pending', '処理中'),
        ('failed', '失敗'),
        ('canceled', 'キャンセル'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='jpy')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    description = models.TextField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - ¥{self.amount}"


class StripeWebhookLog(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"