from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    # 基本URL
    path('', views.IndexView.as_view(), name='index'),
    path('restaurant/<int:pk>/', views.RestaurantDetailView.as_view(), name='detail'),
    
    # お気に入り関連
    path('favorite/toggle/<int:restaurant_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.FavoriteListView.as_view(), name='favorite_list'),
    
    # レビュー関連URL
    path('restaurant/<int:restaurant_id>/review/create/', views.ReviewCreateView.as_view(), name='review_create'),
    path('review/<int:pk>/edit/', views.ReviewUpdateView.as_view(), name='review_edit'),
    path('review/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    
    # 予約関連URL
    path('restaurant/<int:restaurant_id>/reservation/create/', views.ReservationCreateView.as_view(), name='reservation_create'),
    path('reservation/<int:pk>/', views.ReservationDetailView.as_view(), name='reservation_detail'),
    path('reservation/<int:pk>/cancel/', views.ReservationCancelView.as_view(), name='reservation_cancel'),
    path('reservations/', views.ReservationListView.as_view(), name='reservation_list'),
]

