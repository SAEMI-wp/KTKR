from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class EmployeeManager(BaseUserManager):
    """
    ユーザー生成マネージャークラス
    """
    def create_user(self, employee_no, password=None, **extra_fields):
        if not employee_no:
            raise ValueError('社員番号は必須です。')
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
    カスタムユーザーモデル: employee_noをPKとして使用し、usernameの代わりにemployee_noで認証
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
    # 名前関連フィールド
    first_name = models.CharField(max_length=30, verbose_name='名')
    last_name = models.CharField(max_length=30, verbose_name='姓')
    # その他の情報
    place_work = models.CharField(verbose_name='勤務先', max_length=30, blank=True)
    email = models.EmailField(blank=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False, verbose_name='スーパーユーザー')
    
    USERNAME_FIELD = 'employee_no'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = EmployeeManager()
    class Meta:
        verbose_name = '従業員'
        verbose_name_plural = '従業員'
        db_table = 'employee'
        db_table_comment = '社員情報テーブル'
        permissions = [
            ('can_access_admin', '管理者ページへのアクセス権限'),
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
    # 管理者権限がある場合のみTrueを返す（admin用）
    @property
    def is_staff(self):
        return self.has_perm('attendance.can_access_admin')

class Calendar(models.Model):
    """
    カレンダーモデル
    """
    id = models.AutoField(primary_key=True, verbose_name='ID')
    calendar_name = models.CharField(
        verbose_name='現場', 
        max_length=20, 
        null=False
    )
    start_time = models.TimeField(verbose_name='開始時刻', null=False, default='09:00:00')
    end_time = models.TimeField(verbose_name='終了時刻', null=False, default='18:00:00')
    standard_work_hours = models.FloatField(verbose_name='基準時間(Hr)', null=False, default=8.0)
    break_minutes = models.SmallIntegerField(verbose_name='昼休み(分)', null=False, default=60)
    notes = models.TextField(verbose_name='備考', null=True, blank=True)

    class Meta:
        verbose_name = 'カレンダー'
        verbose_name_plural = 'カレンダー'
        db_table = 'calendar'

    def __str__(self):
        return f"{self.calendar_name} - {self.start_time}~{self.end_time}"

class AttendanceMonthly(models.Model):
    """
    月別勤怠モデル
    """
    monthly_id = models.BigAutoField(primary_key=True, verbose_name='個別月日程番号')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employee_no', verbose_name='社員番号')
    year = models.CharField(verbose_name='年', max_length=4)
    month = models.CharField(verbose_name='月', max_length=2)
    project_name = models.CharField(verbose_name='PJ名', max_length=100)
    base_calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, db_column='base_calendar', verbose_name='基準カレンダー')
    is_confirmed = models.BooleanField(default=False, verbose_name='承認済み')
    is_required = models.BooleanField(default=False, verbose_name='承認申請中')

    class Meta:
        verbose_name = '月別勤怠'
        verbose_name_plural = '月別勤怠'
        db_table = 'attendance_monthly'
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
        ('年休', '年休'),
        ('年休(半)', '年休(半)'),
        ('代休', '代休'),
        ('振替(勤)', '振替(勤)'),
        ('振替(休)', '振替(休)'),
        ('特別休暇', '特別休暇'),
        ('欠勤', '欠勤'),
        ('休日', '休日'),
        ('休日(法)', '休日(法)'),
        ('祝日', '祝日'),
        ('その他', 'その他'),
    ]

    daily_id = models.BigAutoField(primary_key=True, verbose_name='日付番号')
    monthly_attendance = models.ForeignKey(AttendanceMonthly, on_delete=models.CASCADE, db_column='monthly_id', verbose_name='個別月日程番号')
    date = models.DateField(verbose_name='日付')
    work_type = models.CharField(verbose_name='勤務区分', max_length=20, choices=WORK_TYPE_CHOICES, null=False, blank=False, default='出勤')
    alternatuve_work_date1 = models.DateField(verbose_name='代休/振替の勤務日1', null=True, blank=True)
    alternatuve_work_date2 = models.DateField(verbose_name='代休/振替の勤務日2', null=True, blank=True)
    alternatuve_work_date3 = models.DateField(verbose_name='代休/振替の勤務日3', null=True, blank=True)
    start_time = models.TimeField(verbose_name='作業開始時刻', null=False, blank=False, default='09:00:00')
    end_time = models.TimeField(verbose_name='作業終了時刻', null=False, blank=False, default='18:00:00')
    notes = models.TextField(verbose_name='実施作業内容/備考', null=True, blank=True)
    is_confirmed = models.BooleanField(verbose_name='確認', default=False, null=False)
    is_required = models.BooleanField(default=False, verbose_name='承認申請中', null=False)
    day_changed = models.BooleanField(verbose_name='日付変更', default=False, null=False)
    
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
    id = models.AutoField(primary_key=True)
    calendar_code = models.ForeignKey(
        Calendar, 
        on_delete=models.CASCADE, 
        verbose_name='カレンダー',
        db_column='calendar_code'
    )
    date = models.DateField('日付')
    category = models.CharField('区分', max_length=20)
    notes = models.CharField('説明', max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'holiday_calendar'
        verbose_name = '休日カレンダー'
        verbose_name_plural = '休日カレンダー一覧'

    def __str__(self):
        return f"{self.calendar_code.calendar_name} {self.date} {self.category}"
