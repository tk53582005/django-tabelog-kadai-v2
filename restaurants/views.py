from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from datetime import datetime, timedelta
from .models import Restaurant, Category, Review, Favorite, Reservation
from .forms import ReviewForm, ReservationForm


class IndexView(ListView):
    model = Restaurant
    template_name = 'restaurants/index.html'
    context_object_name = 'restaurants'
    paginate_by = 12

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        
        # 検索機能
        keyword = self.request.GET.get('keyword', '')
        category_id = self.request.GET.get('category', '')
        
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) | 
                Q(description__icontains=keyword)
            )
        
        if category_id and category_id.isdigit():
            queryset = queryset.filter(category_id=int(category_id))
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['keyword'] = self.request.GET.get('keyword', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class RestaurantDetailView(DetailView):
    model = Restaurant
    template_name = 'restaurants/detail.html'
    context_object_name = 'restaurant'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        restaurant = self.get_object()
        
        # レビュー情報を取得
        reviews = Review.objects.filter(restaurant=restaurant).order_by('-created_at')
        context['reviews'] = reviews
        
        # 平均評価を計算
        avg_score = reviews.aggregate(Avg('rating'))['rating__avg']
        context['avg_score'] = round(avg_score, 1) if avg_score else 0
        context['review_count'] = reviews.count()
        
        # ユーザーがログインしている場合
        if self.request.user.is_authenticated:
            # プレミアム会員のみお気に入り機能を表示
            if hasattr(self.request.user, 'is_premium') and self.request.user.is_premium:
                context['is_favorite'] = Favorite.objects.filter(
                    user=self.request.user, 
                    restaurant=restaurant
                ).exists()
            
            context['user_review'] = reviews.filter(user=self.request.user).first()
            
            # プレミアム会員の場合
            if hasattr(self.request.user, 'is_premium') and self.request.user.is_premium:
                if not context['user_review']:
                    context['review_form'] = ReviewForm()
                context['reservation_form'] = ReservationForm()
        
        return context


@login_required
def toggle_favorite(request, restaurant_id):
    # プレミアム会員チェック
    if not (hasattr(request.user, 'is_premium') and request.user.is_premium):
        messages.error(request, 'お気に入り登録はプレミアム会員限定の機能です。')
        return redirect('restaurants:detail', pk=restaurant_id)
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if request.method == 'POST':
        try:
            favorite = Favorite.objects.get(user=request.user, restaurant=restaurant)
            favorite.delete()
            messages.info(request, f'「{restaurant.name}」をお気に入りから削除しました。')
        except Favorite.DoesNotExist:
            Favorite.objects.create(user=request.user, restaurant=restaurant)
            messages.success(request, f'「{restaurant.name}」をお気に入りに追加しました。')
    
    return redirect('restaurants:detail', pk=restaurant_id)


class FavoriteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Favorite
    template_name = 'restaurants/favorite_list.html'
    context_object_name = 'favorites'
    paginate_by = 12
    
    def test_func(self):
        # プレミアム会員のみ
        return hasattr(self.request.user, 'is_premium') and self.request.user.is_premium
    
    def handle_no_permission(self):
        messages.error(self.request, 'お気に入り機能はプレミアム会員限定です。')
        return redirect('restaurants:index')
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).order_by('-created_at')


class ReviewCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'restaurants/review_create.html'
    
    def test_func(self):
        # プレミアム会員のみ
        return hasattr(self.request.user, 'is_premium') and self.request.user.is_premium
    
    def handle_no_permission(self):
        messages.error(self.request, 'レビュー投稿はプレミアム会員限定です。')
        return redirect('restaurants:index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['restaurant'] = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        return context
    
    def form_valid(self, form):
        restaurant = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        
        # 既にレビューがあるかチェック
        if Review.objects.filter(user=self.request.user, restaurant=restaurant).exists():
            messages.error(self.request, '既にレビューを投稿済みです。')
            return redirect('restaurants:detail', pk=restaurant.pk)
        
        form.instance.user = self.request.user
        form.instance.restaurant = restaurant
        messages.success(self.request, 'レビューを投稿しました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('restaurants:detail', kwargs={'pk': self.kwargs['restaurant_id']})


class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'restaurants/review_edit.html'
    
    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user
    
    def handle_no_permission(self):
        messages.error(self.request, 'このレビューを編集する権限がありません。')
        return redirect('restaurants:index')
    
    def form_valid(self, form):
        messages.success(self.request, 'レビューを更新しました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:mypage')


class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'restaurants/review_delete.html'
    
    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user
    
    def handle_no_permission(self):
        messages.error(self.request, 'このレビューを削除する権限がありません。')
        return redirect('restaurants:index')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'レビューを削除しました。')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('accounts:mypage')


class ReviewListView(LoginRequiredMixin, ListView):
    model = Review
    template_name = 'restaurants/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 10
    
    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).order_by('-created_at')


class ReservationCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'restaurants/reservation_create.html'
    
    def test_func(self):
        # プレミアム会員のみ
        return hasattr(self.request.user, 'is_premium') and self.request.user.is_premium
    
    def handle_no_permission(self):
        messages.error(self.request, '予約機能はプレミアム会員限定です。')
        return redirect('restaurants:index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['restaurant'] = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        return context
    
    def form_valid(self, form):
        restaurant = get_object_or_404(Restaurant, pk=self.kwargs['restaurant_id'])
        
        # 予約日時の妥当性チェック
        reservation_datetime = datetime.combine(
            form.cleaned_data['reservation_date'],
            form.cleaned_data['reservation_time']
        )
        
        if reservation_datetime <= datetime.now():
            messages.error(self.request, '過去の日時には予約できません。')
            return self.form_invalid(form)
        
        form.instance.user = self.request.user
        form.instance.restaurant = restaurant
        messages.success(self.request, '予約を承りました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('restaurants:reservation_detail', kwargs={'pk': self.object.pk})


class ReservationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Reservation
    template_name = 'restaurants/reservation_detail.html'
    context_object_name = 'reservation'
    
    def test_func(self):
        reservation = self.get_object()
        return self.request.user == reservation.user
    
    def handle_no_permission(self):
        messages.error(self.request, 'この予約を表示する権限がありません。')
        return redirect('restaurants:reservation_list')


class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = 'restaurants/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 10
    
    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user).order_by('-reservation_date', '-reservation_time')


class ReservationCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Reservation
    template_name = 'restaurants/reservation_cancel.html'
    fields = []
    
    def test_func(self):
        reservation = self.get_object()
        return (self.request.user == reservation.user and 
                reservation.status == 'confirmed')
    
    def handle_no_permission(self):
        messages.error(self.request, 'この予約をキャンセルする権限がありません。')
        return redirect('restaurants:reservation_list')
    
    def form_valid(self, form):
        # キャンセル期限のチェック（予約日の24時間前まで）
        reservation_datetime = datetime.combine(
            self.object.reservation_date,
            self.object.reservation_time
        )
        
        if reservation_datetime <= datetime.now() + timedelta(hours=24):
            messages.error(self.request, '予約日の24時間前を過ぎているため、キャンセルできません。')
            return redirect('restaurants:reservation_detail', pk=self.object.pk)
        
        form.instance.status = 'cancelled'
        messages.success(self.request, '予約をキャンセルしました。')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('restaurants:reservation_list')
