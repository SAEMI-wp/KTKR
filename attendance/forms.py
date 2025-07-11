from django import forms
from .models import AttendanceMonthly, AttendanceDaily, Employee

class MonthlyAttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceMonthly
        fields = ['project_name', 'base_calendar', 'break_minutes', 'standard_work_hours']
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ○○プロジェクト'}),
            'base_calendar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: カレンダーA'}),
            'break_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'standard_work_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.1}),
        }
        labels = {
            'project_name': 'PJ名',
            'base_calendar': '基準カレンダー',
            'break_minutes': '昼休み区分 (分間)',
            'standard_work_hours': '基準時間 (Hr)',
        }

class DailyAttendanceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        disabled = kwargs.pop('disabled', False)
        super().__init__(*args, **kwargs)
        
        # 모든 필드에 disabled 속성 추가
        for field_name, field in self.fields.items():
            if disabled:
                field.widget.attrs['disabled'] = 'disabled'
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' disabled'
    
    class Meta:
        model = AttendanceDaily
        fields = ['work_type', 'alternative_work_date', 'start_time', 'end_time', 'notes']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'alternative_work_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SignupForm(forms.ModelForm):
    password = forms.CharField(label='パスワード', widget=forms.PasswordInput)
    class Meta:
        model = Employee
        fields = ['employee_no', 'password'] 