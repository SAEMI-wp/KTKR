from django import forms
from .models import AttendanceMonthly, AttendanceDaily, Employee, Calendar

class MonthlyAttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceMonthly
        fields = ['project_name', 'base_calendar']
        widgets = {
            'project_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ○○プロジェクト'}),
            'base_calendar': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'project_name': 'PJ名',
            'base_calendar': '基準カレンダー',
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
        fields = ['work_type', 'alternative_work_date1', 'alternative_work_date2', 'alternative_work_date3', 'start_time', 'end_time', 'notes']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'alternative_work_date1': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'alternative_work_date2': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'alternative_work_date3': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SignupForm(forms.ModelForm):
    password = forms.CharField(label='パスワード', widget=forms.PasswordInput)
    class Meta:
        model = Employee
        fields = ['employee_no', 'password'] 