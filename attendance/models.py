from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class EmployeeManager(BaseUserManager):
    """
    사용자 생성 매니저 클래스
    """
    def create_user(self, employee_no, password=None, **extra_fields):
        if not employee_no:
            raise ValueError('사원번호는 필수입니다.')
        user = self.model(employee_no=employee_no, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_no, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(employee_no, password, **extra_fields)

class Employee(AbstractBaseUser, PermissionsMixin):
    """
    커스텀 User 모델: employee_no를 PK로 사용하며, username 대신 employee_no로 인증
    """
    employee_no = models.CharField(
        max_length=6,
        primary_key=True,
        unique=True,
        verbose_name='社員番号',
        help_text='6桁の社員番号を入力してください (例: 123456)',
        error_messages={
            'unique': 'この社員番号は既に使用されています。',
            'invalid': '社員番号は6桁の数字で入力してください。',
        },
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='社員番号は6桁の数字で入力してください。',
            ),
        ]
    )
    # 이름 관련 필드
    first_name = models.CharField(max_length=30, verbose_name='名前')
    last_name = models.CharField(max_length=30, verbose_name='姓')
    # 기타 정보
    place_work = models.CharField(verbose_name='勤務先', max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    USERNAME_FIELD = 'employee_no'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = EmployeeManager()
    class Meta:
        verbose_name = '従業員'
        verbose_name_plural = '従業員'
        db_table = 'employee'
        db_table_comment = '社員情報テーブル'
        permissions = [
            ('can_access_admin', '관리자 페이지 접근 권한'),
        ]
    def __str__(self):
        return f"{self.employee_no} - {self.last_name} {self.first_name}"
    @property
    def display_name(self):
        return f"{self.last_name} {self.first_name}" or f"{self.employee_no}"
    def clean(self):
        super().clean()
        if self.employee_no and not self.employee_no.isdigit():
            raise models.ValidationError({
                'employee_no': '社員番号は6桁の数字で入力してください。'
            })

class AttendanceMonthly(models.Model):
    """
    月別勤怠モデル
    """
    monthly_id = models.BigAutoField(primary_key=True, verbose_name='個別月日程番号')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='社員番号')
    year = models.CharField(verbose_name='年', max_length=4)
    month = models.CharField(verbose_name='月', max_length=2)
    project_name = models.CharField(verbose_name='PJ名', max_length=100)
    base_calendar = models.CharField(verbose_name='基準カレンダー', max_length=20)
    break_minutes = models.PositiveIntegerField(verbose_name='昼休み区分 (分間)')
    standard_work_hours = models.FloatField(verbose_name='基準時間 (Hr)')
    is_confirmed = models.BooleanField(default=False, verbose_name='承認済み')
    is_required = models.BooleanField(default=False, verbose_name='承認申請中')

    class Meta:
        verbose_name = '月別勤怠'
        verbose_name_plural = '月別勤怠'
        db_table = 'attendance_monthly'
        # 社員、年、月でユニークにする
        constraints = [
            models.UniqueConstraint(fields=['employee', 'year', 'month'], name='unique_monthly_attendance')
        ]

    def __str__(self):
        return f"{int(self.employee.employee_no):06d} - {self.year}/{self.month}"

class AttendanceDaily(models.Model):
    """
    日別勤怠モデル
    """
    WORK_TYPE_CHOICES = [
        ('出勤', '出勤'),
        ('有給', '有給'),
        ('有給(半)', '有給(半)'),
        ('代休', '代休'),
        ('振替(休)', '振替(休)'),
        ('振替(法)', '振替(法)'),
        ('振替(勤)', '振替(勤)'),
        ('特別休暇', '特別休暇'),
        ('欠勤', '欠勤'),
        ('休日', '休日'),
        ('休日(法)', '休日(法)'),
        ('祝日', '祝日'),
        ('その他', 'その他'),
    ]

    daily_id = models.BigAutoField(primary_key=True, verbose_name='日付番号')
    monthly_attendance = models.ForeignKey(AttendanceMonthly, on_delete=models.CASCADE, verbose_name='個別月日程番号')
    date = models.DateField(verbose_name='日付')
    work_type = models.CharField(verbose_name='勤務区分', max_length=20, choices=WORK_TYPE_CHOICES, null=True, blank=True)
    alternative_work_date = models.DateField(verbose_name='代休/振替の勤務日', null=True, blank=True)
    start_time = models.TimeField(verbose_name='作業開始時刻', null=True, blank=True)
    end_time = models.TimeField(verbose_name='作業終了時刻', null=True, blank=True)
    notes = models.TextField(verbose_name='実施作業内容/備考', null=True, blank=True)
    is_confirmed = models.BooleanField(verbose_name='確認', default=False)
    is_required = models.BooleanField(default=False, verbose_name='承認申請中')
    
    class Meta:
        verbose_name = '日別勤怠'
        verbose_name_plural = '日別勤怠'
        db_table = 'attendance_daily'
        # 日付と月次勤怠でユニークにする
        constraints = [
            models.UniqueConstraint(fields=['monthly_attendance', 'date'], name='unique_daily_attendance')
        ]
        ordering = ['date']

    def __str__(self):
        return f"{int(self.monthly_attendance.employee.employee_no):06d} - {self.date}"

class PaidLeave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='社員')
    year = models.CharField(max_length=4, verbose_name='年')
    total_days = models.PositiveIntegerField(verbose_name='付与日数')
    used_days = models.PositiveIntegerField(default=0, verbose_name='使用日数')
    notes = models.CharField(max_length=100, blank=True, verbose_name='備考')
    class Meta:
        verbose_name = '有給休暇'
        verbose_name_plural = '有給休暇'
        db_table = 'paid_leave'
        unique_together = ('employee', 'year')
    def __str__(self):
        return f"{self.employee} {self.year}年 有給休暇"

class PaySlip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='社員')
    year = models.CharField(max_length=4, verbose_name='年')
    month = models.CharField(max_length=2, verbose_name='月')
    payment = models.PositiveIntegerField(verbose_name='支給額', default=0)
    deduction = models.PositiveIntegerField(verbose_name='控除額', default=0)
    net_payment = models.PositiveIntegerField(verbose_name='差引支給額', default=0)
    notes = models.CharField(max_length=100, blank=True, verbose_name='備考')
    class Meta:
        verbose_name = '給与明細書'
        verbose_name_plural = '給与明細書'
        db_table = 'pay_slip'
        unique_together = ('employee', 'year', 'month')
    def __str__(self):
        return f"{self.employee} {self.year}年{self.month}月 給与明細書"

class HolidayCalendar(models.Model):
    CALENDAR_CHOICES = [
        ('共通', '共通'),
        ('Techave', 'Techave'),
        ('H大甕', 'H大甕'),
    ]
    calendar_name = models.CharField('カレンダー名', max_length=20, choices=CALENDAR_CHOICES)
    date = models.DateField('日付')
    category = models.CharField('区分', max_length=20)

    class Meta:
        db_table = 'holiday_calendar'
        unique_together = ('calendar_name', 'date', 'category')
        verbose_name = '休日カレンダー'
        verbose_name_plural = '休日カレンダー一覧'

    def __str__(self):
        return f"{self.calendar_name} {self.date} {self.category}"
