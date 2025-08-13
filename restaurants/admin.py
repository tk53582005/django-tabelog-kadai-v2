from django.contrib import admin
from .models import Category, Restaurant, Review, Reservation, Favorite

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'address', 'phone_number', 'opening_time', 'closing_time')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'address', 'description')
    ordering = ('-created_at',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('restaurant__name', 'user__email', 'comment')
    ordering = ('-created_at',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'user', 'reservation_date', 'reservation_time', 'number_of_people', 'status')
    list_filter = ('status', 'reservation_date', 'created_at')
    search_fields = ('restaurant__name', 'user__email')
    ordering = ('-reservation_date', '-reservation_time')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at')
    search_fields = ('user__email', 'restaurant__name')
    ordering = ('-created_at',)


