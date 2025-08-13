from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    # 住所・連絡先
    address = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    
    # 営業時間
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    regular_holiday = models.CharField(max_length=100, blank=True)
    
    # 画像・URL
    image = models.ImageField(upload_to='restaurants/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    
    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_average_rating(self):
        # 平均評価を取得
        reviews = self.review_set.all()
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    
    # 追加フィールド
    is_approved = models.BooleanField(default=True)
    helpful_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'restaurant']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.user.email} ({self.rating}★)"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('confirmed', '確定'),
        ('cancelled', 'キャンセル'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    
    # 予約情報
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    number_of_people = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.reservation_date} {self.reservation_time}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'restaurant']
    
    def __str__(self):
        return f"{self.user.email} - {self.restaurant.name}"


