from django import forms
from .models import CustomUser


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'postal_code', 'address', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '太郎'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '山田'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '460-0008',
                'pattern': '[0-9]{3}-[0-9]{4}',
                'title': '郵便番号は000-0000の形式で入力してください'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '愛知県名古屋市中区栄3-1-1'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '090-1234-5678',
                'pattern': '[0-9]{2,4}-[0-9]{2,4}-[0-9]{3,4}',
                'title': '電話番号は000-0000-0000の形式で入力してください'
            }),
        }
        labels = {
            'first_name': '名',
            'last_name': '姓',
            'postal_code': '郵便番号',
            'address': '住所',
            'phone_number': '電話番号',
        }
    
    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code and not postal_code.replace('-', '').isdigit():
            raise forms.ValidationError('郵便番号は数字とハイフンのみ入力可能です。')
        return postal_code
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.replace('-', '').isdigit():
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力可能です。')
        return phone_number