from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta, time
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
    # 30分刻みの時間選択肢
    TIME_CHOICES = [
        ('18:00:00', '18:00'),
        ('18:30:00', '18:30'),
        ('19:00:00', '19:00'),
        ('19:30:00', '19:30'),
        ('20:00:00', '20:00'),
        ('20:30:00', '20:30'),
        ('21:00:00', '21:00'),
    ]
    
    class Meta:
        model = Reservation
        fields = ['reservation_date', 'reservation_time', 'number_of_people']
        widgets = {
            'reservation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'reservation_time': forms.Select(
                choices=TIME_CHOICES,
                attrs={'class': 'form-select'}
            ),
            'number_of_people': forms.Select(
                choices=[(i, f'{i}名') for i in range(1, 11)],
                attrs={'class': 'form-select'}
            )
        }
        labels = {
            'reservation_date': '予約日',
            'reservation_time': '予約時間',
            'number_of_people': '人数'
        }
    
    def clean_reservation_date(self):
        reservation_date = self.cleaned_data.get('reservation_date')
        
        if not reservation_date:
            raise ValidationError('予約日を選択してください。')
        
        # 本日以降の日付のみ許可
        if reservation_date < timezone.now().date():
            raise ValidationError('本日以降の日付を選択してください。')
        
        # 30日以降の予約は不可
        max_date = timezone.now().date() + timedelta(days=30)
        if reservation_date > max_date:
            raise ValidationError('予約は30日先まで可能です。')
        
        return reservation_date
    
    def clean_reservation_time(self):
        reservation_time = self.cleaned_data.get('reservation_time')
        
        if not reservation_time:
            raise ValidationError('予約時間を選択してください。')
        
        # 30分刻みの時間のみ許可
        valid_times = [
            time(18, 0), time(18, 30), time(19, 0), time(19, 30),
            time(20, 0), time(20, 30), time(21, 0)
        ]
        
        # 文字列の場合はtimeオブジェクトに変換
        if isinstance(reservation_time, str):
            try:
                reservation_time = datetime.strptime(reservation_time, '%H:%M:%S').time()
            except ValueError:
                try:
                    reservation_time = datetime.strptime(reservation_time, '%H:%M').time()
                except ValueError:
                    raise ValidationError('正しい時間形式を選択してください。')
        
        if reservation_time not in valid_times:
            raise ValidationError('営業時間内の30分刻みの時間を選択してください。（18:00-21:00）')
        
        return reservation_time
    
    def clean(self):
        cleaned_data = super().clean()
        reservation_date = cleaned_data.get('reservation_date')
        reservation_time = cleaned_data.get('reservation_time')
        
        if reservation_date and reservation_time:
            # 現在時刻から2時間後以降の予約のみ受付
            reservation_datetime = datetime.combine(reservation_date, reservation_time)
            min_datetime = timezone.now() + timedelta(hours=2)
            
            if reservation_datetime < min_datetime:
                raise ValidationError('予約は2時間後以降の時間を選択してください。')
        
        return cleaned_data