from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_premium', 'is_staff', 'date_joined')
    list_filter = ('is_premium', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('date_joined',)  # created_at → date_joined に変更
    
    # フィールドセットの設定
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('first_name', 'last_name', 'postal_code', 'address', 'phone_number')}),
        ('権限', {'fields': ('is_premium', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要な日付', {'fields': ('last_login', 'date_joined')}),
    )
    
    # 新規作成時のフィールドセット
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_premium'),
        }),
    )
    
    # 読み取り専用フィールド
    readonly_fields = ('date_joined', 'last_login')


# 不要なモデルを管理画面から削除
try:
    from allauth.account.models import EmailAddress
    admin.site.unregister(EmailAddress)
except:
    pass

try:
    from django.contrib.sites.models import Site
    admin.site.unregister(Site)
except:
    pass

try:
    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
    admin.site.unregister(SocialAccount)
    admin.site.unregister(SocialApp) 
    admin.site.unregister(SocialToken)
except:
    pass
