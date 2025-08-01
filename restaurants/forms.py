from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Review, Reservation


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i}つ星') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'お店の感想をお聞かせください...'
            })
        }
        labels = {
            'rating': '評価',
            'comment': 'レビュー内容'
        }
    
    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        if len(comment.strip()) < 10:
            raise forms.ValidationError('レビューは10文字以上で入力してください。')
        return comment


class ReservationForm(forms.ModelForm):
    # 時間選択肢
    TIME_CHOICES = [
        ('18:00', '18:00'),
        ('18:30', '18:30'),
        ('19:00', '19:00'),
        ('19:30', '19:30'),
        ('20:00', '20:00'),
        ('20:30', '20:30'),
        ('21:00', '21:00'),
    ]
    
    reservation_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='予約時間'
    )
    
    class Meta:
        model = Reservation
        fields = ['reservation_date', 'reservation_time', 'number_of_people']
        widgets = {
            'reservation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'number_of_people': forms.Select(
                choices=[(i, f'{i}名') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            )
        }
        labels = {
            'reservation_date': '予約日',
            'number_of_people': '人数'
        }
    
    def clean_reservation_date(self):
        reservation_date = self.cleaned_data.get('reservation_date')
        
        if not reservation_date:
            raise ValidationError('予約日を選択してください。')
        
        # 本日以降の日付のみ許可
        if reservation_date < timezone.now().date():
            raise ValidationError('本日以降の日付を選択してください。')
        
        return reservation_date
    
    def clean_reservation_time(self):
        reservation_time_str = self.cleaned_data.get('reservation_time')
        
        if not reservation_time_str:
            raise ValidationError('予約時間を選択してください。')
        
        # 文字列をtimeオブジェクトに変換
        try:
            reservation_time = datetime.strptime(reservation_time_str, '%H:%M').time()
        except ValueError:
            raise ValidationError('正しい時間形式を選択してください。')
        
        return reservation_time