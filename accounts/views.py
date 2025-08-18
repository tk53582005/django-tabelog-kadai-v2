from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import stripe
import json
from datetime import datetime
from .models import CustomUser, Subscription, PaymentHistory, StripeWebhookLog
from .forms import UserProfileForm

# Stripe設定
stripe.api_key = settings.STRIPE_SECRET_KEY


class MyPageView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/mypage.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # プレミアム会員のみお気に入り店舗を取得
        from restaurants.models import Favorite, Review, Reservation
        if user.is_premium:
            context['favorite_restaurants'] = Favorite.objects.filter(user=user)[:5]
        
        # 最近のレビューを取得
        context['recent_reviews'] = Review.objects.filter(user=user).order_by('-created_at')[:5]
        
        # プレミアム会員の場合、予約履歴も取得
        if user.is_premium:
            context['recent_reservations'] = Reservation.objects.filter(user=user).order_by('-created_at')[:5]
        
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:mypage')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'プロフィールを更新しました。')
        return super().form_valid(form)


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'パスワードを変更しました。')
            return redirect('accounts:mypage')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})


# カード管理機能

class CardManageView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/card_manage.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_premium:
            messages.error(request, 'プレミアム会員のみ利用可能です。')
            return redirect('accounts:mypage')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.stripe_customer_id:
            try:
                # 支払い方法一覧を取得
                payment_methods = stripe.PaymentMethod.list(
                    customer=user.stripe_customer_id,
                    type="card"
                )
                context['payment_methods'] = payment_methods.data
                
                # デフォルトの支払い方法を取得
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                context['default_payment_method'] = customer.invoice_settings.default_payment_method
                
            except:
                messages.error(self.request, 'カード情報の取得に失敗しました。')
        
        return context


class CardAddView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/card_add.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_premium:
            messages.error(request, 'プレミアム会員のみ利用可能です。')
            return redirect('accounts:mypage')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = settings.STRIPE_PUBLIC_KEY
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            payment_method_id = request.POST.get('payment_method_id')
            user = request.user
            
            if not payment_method_id:
                messages.error(request, 'カード情報が正しく送信されませんでした。')
                return self.get(request, *args, **kwargs)
            
            # Stripe顧客がない場合は作成
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': user.id}
                )
                user.stripe_customer_id = customer.id
                user.save()
            
            # 支払い方法を顧客にアタッチ
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id,
            )
            
            # デフォルトの支払い方法として設定
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )
            
            messages.success(request, 'カードを追加しました。')
            return redirect('accounts:card_manage')
            
        except:
            messages.error(request, 'カードの追加に失敗しました。')
            return self.get(request, *args, **kwargs)


class CardChangeView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/card_change.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_premium:
            messages.error(request, 'プレミアム会員のみ利用可能です。')
            return redirect('accounts:mypage')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_public_key'] = settings.STRIPE_PUBLIC_KEY
        
        user = self.request.user
        if user.stripe_customer_id:
            try:
                # 現在の支払い方法を取得
                payment_methods = stripe.PaymentMethod.list(
                    customer=user.stripe_customer_id,
                    type="card"
                )
                if payment_methods.data:
                    context['current_payment_method'] = payment_methods.data[0]
            except:
                pass
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            payment_method_id = request.POST.get('payment_method_id')
            old_payment_method_id = request.POST.get('old_payment_method_id')
            user = request.user
            
            if not payment_method_id:
                messages.error(request, 'カード情報が正しく送信されませんでした。')
                return self.get(request, *args, **kwargs)
            
            # 新しい支払い方法を顧客にアタッチ
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id,
            )
            
            # デフォルトの支払い方法として設定
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )
            
            # 古い支払い方法を削除
            if old_payment_method_id:
                try:
                    stripe.PaymentMethod.detach(old_payment_method_id)
                except:
                    pass
            
            messages.success(request, 'カード情報を変更しました。')
            return redirect('accounts:card_manage')
            
        except:
            messages.error(request, 'カードの変更に失敗しました。')
            return self.get(request, *args, **kwargs)


@login_required
@require_POST
def set_default_card(request):
    try:
        payment_method_id = request.POST.get('payment_method_id')
        user = request.user
        
        if not payment_method_id:
            return JsonResponse({'error': '支払い方法IDが必要です'}, status=400)
        
        if not user.stripe_customer_id:
            return JsonResponse({'error': 'カスタマーIDが設定されていません'}, status=400)
        
        # デフォルトの支払い方法として設定
        stripe.Customer.modify(
            user.stripe_customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id,
            },
        )
        
        return JsonResponse({'success': True, 'message': 'メインカードを設定しました'})
        
    except:
        return JsonResponse({'error': 'エラーが発生しました'}, status=500)


@login_required
@require_POST
def remove_payment_method(request):
    try:
        payment_method_id = request.POST.get('payment_method_id')
        user = request.user
        
        if not payment_method_id:
            return JsonResponse({'error': '支払い方法IDが必要です'}, status=400)
        
        # プレミアム会員で支払い方法が複数ある場合のみ削除可能
        if user.is_premium and user.stripe_customer_id:
            # 現在登録されている支払い方法の数を確認
            payment_methods = stripe.PaymentMethod.list(
                customer=user.stripe_customer_id,
                type="card"
            )
            
            if len(payment_methods.data) <= 1:
                return JsonResponse({
                    'error': '最後の支払い方法は削除できません。代替のカードを先に登録してください。'
                }, status=400)
            
            # デフォルトの支払い方法を確認
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
            default_payment_method = customer.invoice_settings.default_payment_method
            
            if payment_method_id == default_payment_method:
                # 削除するカードがデフォルトの場合、他のカードをデフォルトに設定
                other_payment_methods = [pm for pm in payment_methods.data if pm.id != payment_method_id]
                if other_payment_methods:
                    stripe.Customer.modify(
                        user.stripe_customer_id,
                        invoice_settings={
                            'default_payment_method': other_payment_methods[0].id,
                        },
                    )
        
        # 支払い方法をデタッチ
        stripe.PaymentMethod.detach(payment_method_id)
        
        return JsonResponse({'success': True, 'message': 'カードを削除しました'})
        
    except stripe.error.StripeError as e:
        return JsonResponse({'error': f'Stripeエラー: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'エラーが発生しました: {str(e)}'}, status=500)


@login_required
def billing_portal(request):
    try:
        user = request.user
        
        if not user.stripe_customer_id:
            messages.error(request, 'カスタマーIDが設定されていません。')
            return redirect('accounts:mypage')
        
        # 請求ポータルセッションを作成
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.build_absolute_uri(reverse('accounts:mypage'))
        )
        
        return redirect(session.url)
        
    except:
        messages.error(request, '請求ポータルへのアクセスに失敗しました。')
        return redirect('accounts:mypage')


# Stripe決済システム

class SubscriptionPlanView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/subscription_plan.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_settings'] = settings.SUBSCRIPTION_SETTINGS
        context['stripe_public_key'] = settings.STRIPE_PUBLIC_KEY
        
        # 既にプレミアム会員の場合は現在のサブスクリプション情報を追加
        if self.request.user.is_premium:
            context['current_subscription'] = self.request.user.get_subscription()
        
        return context


@login_required
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)
    
    try:
        user = request.user
        
        # 既にプレミアム会員の場合は処理を停止
        if user.is_premium:
            return JsonResponse({'error': '既にプレミアム会員です'}, status=400)
        
        # Stripe顧客を作成または取得
        if user.stripe_customer_id:
            customer_id = user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={'user_id': user.id}
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            user.save()
        
        # Checkout セッションを作成
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': settings.STRIPE_PRICE_ID_PREMIUM,
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri(reverse('accounts:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('accounts:payment_cancel')),
            metadata={
                'user_id': user.id,
            }
        )
        
        return JsonResponse({'checkout_url': checkout_session.url})
    
    except:
        return JsonResponse({'error': '予期しないエラーが発生しました'}, status=500)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/payment_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = self.request.GET.get('session_id')
        
        if session_id:
            try:
                # Checkoutセッションの詳細を取得
                session = stripe.checkout.Session.retrieve(session_id)
                context['session'] = session
                
                # サブスクリプション情報を取得
                if session.subscription:
                    subscription = stripe.Subscription.retrieve(session.subscription)
                    context['subscription'] = subscription
                    
            except:
                messages.error(self.request, '決済情報の取得に失敗しました。')
        
        return context


class PaymentCancelView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/payment_cancel.html'


class SubscriptionManageView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/subscription_manage.html'
    
    def dispatch(self, request, *args, **kwargs):
        # プレミアム会員のみアクセス可能
        if not request.user.is_premium:
            messages.error(request, 'プレミアム会員のみアクセス可能です。')
            return redirect('accounts:subscription_plan')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # サブスクリプション情報
        subscription = user.get_subscription()
        context['subscription'] = subscription
        
        # 決済履歴
        context['payment_history'] = PaymentHistory.objects.filter(user=user).order_by('-created_at')
        
        return context


@login_required
@require_POST
def cancel_subscription(request):
    try:
        user = request.user
        
        # プレミアム会員でない場合
        if not user.is_premium:
            return JsonResponse({
                'error': 'プレミアム会員ではありません'
            }, status=400)
        
        # データベースからアクティブなサブスクリプションを取得
        subscription = Subscription.objects.filter(
            user=user, 
            status='active'
        ).first()
        
        if not subscription:
            # Stripeから直接サブスクリプション情報を取得して同期
            if user.stripe_customer_id:
                try:
                    stripe_subscriptions = stripe.Subscription.list(
                        customer=user.stripe_customer_id,
                        status='active'
                    )
                    
                    if stripe_subscriptions.data:
                        # アクティブなサブスクリプションが見つかった場合、データベースに同期
                        stripe_sub = stripe_subscriptions.data[0]
                        
                        subscription, created = Subscription.objects.update_or_create(
                            user=user,
                            stripe_subscription_id=stripe_sub.id,
                            defaults={
                                'stripe_customer_id': user.stripe_customer_id,
                                'stripe_price_id': stripe_sub.items.data[0].price.id,
                                'status': stripe_sub.status,
                                'current_period_start': datetime.fromtimestamp(stripe_sub.current_period_start),
                                'current_period_end': datetime.fromtimestamp(stripe_sub.current_period_end),
                            }
                        )
                    else:
                        return JsonResponse({
                            'error': 'アクティブなサブスクリプションがありません'
                        }, status=400)
                        
                except stripe.error.StripeError as e:
                    return JsonResponse({
                        'error': f'Stripeエラー: サブスクリプション情報の取得に失敗しました'
                    }, status=500)
            else:
                return JsonResponse({
                    'error': 'アクティブなサブスクリプションがありません'
                }, status=400)
        
        # Stripeでサブスクリプションをキャンセル（期間終了時にキャンセル）
        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # データベースのステータスも更新
            subscription.status = 'active'  # 期間終了まではアクティブのまま
            subscription.save()
            
            messages.success(request, f'サブスクリプションのキャンセルを受け付けました。{subscription.current_period_end.strftime("%Y年%m月%d日")}まで利用可能です。')
            
            return JsonResponse({
                'success': True,
                'message': 'サブスクリプションのキャンセルを受け付けました。'
            })
            
        except stripe.error.StripeError as e:
            return JsonResponse({
                'error': f'Stripeエラー: {str(e)}'
            }, status=500)
    
    except Exception as e:
        return JsonResponse({
            'error': f'予期しないエラーが発生しました: {str(e)}'
        }, status=500)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        # WebHookの署名を検証
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except:
        return HttpResponse(status=400)
    
    # WebHookログを記録
    webhook_log, created = StripeWebhookLog.objects.get_or_create(
        stripe_event_id=event['id'],
        defaults={
            'event_type': event['type'],
            'processed': False
        }
    )
    
    if not created and webhook_log.processed:
        return HttpResponse(status=200)
    
    try:
        # イベントタイプに応じた処理
        if event['type'] == 'checkout.session.completed':
            handle_checkout_session_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])
        
        # 処理完了をマーク
        webhook_log.processed = True
        webhook_log.save()
        
    except Exception as e:
        webhook_log.error_message = str(e)
        webhook_log.save()
        return HttpResponse(status=500)
    
    return HttpResponse(status=200)


def handle_checkout_session_completed(session_data):
    """
    Checkout セッション完了時の処理
    プレミアム会員への切り替えを実行
    """
    try:
        # セッションからカスタマーIDを取得
        customer_id = session_data['customer']
        
        # ユーザーを特定
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
        
        # プレミアム会員に変更
        user.is_premium = True
        user.save()
        
        # サブスクリプション情報を取得して保存
        if session_data.get('subscription'):
            subscription_id = session_data['subscription']
            subscription_data = stripe.Subscription.retrieve(subscription_id)
            
            # Subscriptionレコードを作成
            Subscription.objects.update_or_create(
                user=user,
                stripe_subscription_id=subscription_id,
                defaults={
                    'stripe_customer_id': customer_id,
                    'stripe_price_id': subscription_data['items']['data'][0]['price']['id'],
                    'status': subscription_data['status'],
                    'current_period_start': datetime.fromtimestamp(subscription_data['current_period_start']),
                    'current_period_end': datetime.fromtimestamp(subscription_data['current_period_end']),
                }
            )
        
    except Exception as e:
        # エラーログを出力
        print(f"Checkout session completion error: {e}")
        raise


def handle_subscription_created(subscription_data):
    try:
        # 顧客情報からユーザーを特定
        customer = stripe.Customer.retrieve(subscription_data['customer'])
        user = CustomUser.objects.get(stripe_customer_id=customer.id)
        
        # サブスクリプションを作成
        Subscription.objects.create(
            user=user,
            stripe_subscription_id=subscription_data['id'],
            stripe_customer_id=customer.id,
            stripe_price_id=subscription_data['items']['data'][0]['price']['id'],
            status=subscription_data['status'],
            current_period_start=datetime.fromtimestamp(subscription_data['current_period_start']),
            current_period_end=datetime.fromtimestamp(subscription_data['current_period_end']),
        )
        
    except:
        pass


def handle_subscription_updated(subscription_data):
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_data['id']
        )
        
        # ステータスと期間を更新
        subscription.status = subscription_data['status']
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        subscription.save()
        
    except:
        pass


def handle_subscription_deleted(subscription_data):
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_data['id']
        )
        
        subscription.status = 'canceled'
        subscription.save()
        
    except:
        pass


def handle_payment_succeeded(invoice_data):
    try:
        # サブスクリプションを特定
        subscription = Subscription.objects.get(
            stripe_subscription_id=invoice_data['subscription']
        )
        
        # 決済履歴を作成
        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            stripe_payment_intent_id=invoice_data['payment_intent'],
            stripe_invoice_id=invoice_data['id'],
            amount=invoice_data['amount_paid'] / 100,
            currency=invoice_data['currency'],
            status='succeeded',
            description="プレミアム会員 月額料金",
            paid_at=datetime.fromtimestamp(invoice_data['status_transitions']['paid_at']),
        )
        
    except:
        pass


def handle_payment_failed(invoice_data):
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=invoice_data['subscription']
        )
        
        # 失敗した決済履歴を作成
        PaymentHistory.objects.create(
            user=subscription.user,
            subscription=subscription,
            stripe_payment_intent_id=invoice_data.get('payment_intent', ''),
            stripe_invoice_id=invoice_data['id'],
            amount=invoice_data['amount_due'] / 100,
            currency=invoice_data['currency'],
            status='failed',
            description="プレミアム会員 月額料金（決済失敗）",
            failure_reason='決済に失敗しました',
        )
        
    except:
        pass