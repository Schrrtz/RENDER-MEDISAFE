from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')
            
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', True)
        return self.create_user(username, email, password, **extra_fields)

class Doctor(models.Model):
    doctor_id = models.AutoField(primary_key=True)
    user = models.OneToOneField('User', on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.IntegerField()
    availability = models.JSONField(default=dict)  # Store availability schedule
    contact_info = models.TextField()

    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialization}"

class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.TextField()
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('lab_tech', 'Lab Technician'),
        ('patient', 'Patient')
    ])
    status = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Required for Django authentication
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)  # Required field
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'role']

    def save(self, *args, **kwargs):
        if not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
            self.password = make_password(self.password)
        super(User, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    def get_full_name(self):
        profile = getattr(self, 'userprofile', None)
        if profile:
            return f"{profile.first_name} {profile.last_name}".strip()
        return self.username

    def get_short_name(self):
        profile = getattr(self, 'userprofile', None)
        if profile and profile.first_name:
            return profile.first_name
        return self.username

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    class Meta:
        db_table = 'users'  # Specify the table name in MySQL



        

class UserProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, to_field='user_id')
    first_name = models.CharField(max_length=50)  # NOT NULL
    middle_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50)  # NOT NULL
    birthday = models.DateField(null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    sex = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        null=True, 
        blank=True
    )
    civil_status = models.CharField(
        max_length=20,
        choices=[
            ('single', 'Single'),
            ('married', 'Married'),
            ('divorced', 'Divorced'),
            ('widowed', 'Widowed'),
            ('separated', 'Separated')
        ],
        null=True,
        blank=True
    )
    address = models.TextField(null=True, blank=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    relationship_to_patient = models.CharField(max_length=50, null=True, blank=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    photo_url = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    phone_type = models.CharField(
        max_length=10,
        choices=[
            ('mobile', 'Mobile'),
            ('home', 'Home'),
            ('work', 'Work'),
            ('other', 'Other')
        ],
        null=True,
        blank=True
    )
    data_privacy_consent = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_profiles'  # Specify the table name in MySQL

    @property
    def birth_date(self):
        """Compatibility accessor: some templates and views expect `birth_date`.
        The field was renamed to `birthday` in a migration; provide a proxy
        to avoid touching many templates at once.
        """
        return self.birthday

class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('account', 'Account'),
        ('urgent', 'Urgent'),
        ('appointment', 'Appointment'),
        ('lab_result', 'Lab Result'),
        ('system', 'System'),
        ('password_reset', 'Password Reset Request')
    ])
    is_read = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    related_id = models.IntegerField(null=True, blank=True)  # ID of related appointment, lab result, etc.
    file = models.FileField(upload_to='notifications/', null=True, blank=True)  # For ID photos and other attachments
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type}: {self.title} - {self.user.username}"

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patients', limit_choices_to={'role': 'client'}, null=True, blank=True)
    medical_record_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], null=True, blank=True)
    blood_type = models.CharField(max_length=3, choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    conditions = models.TextField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patients'

    def __str__(self):
        try:
            user_profile = self.user.userprofile
            name = f"{user_profile.first_name} {user_profile.last_name}"
        except:
            name = self.user.username
        return f"{name} - MRN: {self.medical_record_number or 'N/A'}"

class Appointment(models.Model):
    consultation_id = models.AutoField(primary_key=True)
    appointment_number = models.CharField(max_length=50, null=True, blank=True, unique=False)
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        db_column='patient_id',
        to_field='user_id',
        related_name='patient_consultations'
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        db_column='doctor_id',
        to_field='doctor_id',
        related_name='doctor_consultations'
    )
    consultation_type = models.CharField(
        max_length=20,
        choices=[('F2F', 'Face to Face'), ('Tele', 'Tele-Consultation')]
    )
    consultation_date = models.DateField()
    consultation_time = models.TimeField()
    approval_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')],
        default='Scheduled'
    )
    notes = models.TextField(null=True, blank=True)
    meeting_link = models.TextField(null=True, blank=True)
    reason_for_visit = models.TextField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=30)
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'

    def __str__(self):
        return f"{self.consultation_type} - {self.doctor.get_full_name()} with {self.patient.get_full_name()}"

class LabResult(models.Model):
    lab_result_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        db_column='user_id',
        to_field='user_id',
        related_name='lab_results'
    )
    lab_type = models.CharField(max_length=100)
    result_file = models.TextField()  # Store file path or base64 data
    file_type = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='uploaded_by_id',
        to_field='user_id',
        related_name='uploaded_lab_results'
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'lab_results'
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.lab_type} - {self.user.username} ({self.upload_date.strftime('%Y-%m-%d')})"

class LiveAppointment(models.Model):
    """Live consultation session linked to an appointment"""
    live_appointment_id = models.AutoField(primary_key=True)
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='live_session'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('waiting', 'Waiting'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        default='waiting'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    # Human-friendly display ID (e.g. LAP001). Generated when the
    # live appointment is created/started. Kept separate from the
    # AutoField primary key to preserve DB integrity.
    live_appointment_number = models.CharField(max_length=6, unique=True, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    session_duration = models.IntegerField(null=True, blank=True)  # Duration in minutes
    
    # Medical Data
    vital_signs = models.JSONField(default=dict)  # Store BP, HR, Temp, etc.
    symptoms = models.TextField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    clinical_notes = models.TextField(null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True)
    follow_up_notes = models.TextField(null=True, blank=True)
    
    # Doctor's observations
    doctor_notes = models.TextField(null=True, blank=True)
    recommendations = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'live_appointments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Live Session - {self.appointment.doctor.get_full_name()} with {self.appointment.patient.get_full_name()}"
    
    def get_duration(self):
        """Calculate session duration in minutes"""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return int(duration.total_seconds() / 60)
        return None

    def generate_live_appointment_number(self):
        """Generate a unique LAP### code (LAP + zero-padded 3-digit number).
        Uses existing records to pick the next number. This is simple and
        sufficient for low-concurrency environments; if you need strong
        guarantees under heavy concurrent creation, replace with a DB-side
        sequence or locking.
        """
        prefix = 'LAP'
        from django.db.models import Max
        # Find max numeric suffix among existing LAP codes
        vals = LiveAppointment.objects.filter(live_appointment_number__startswith=prefix).values_list('live_appointment_number', flat=True)
        max_num = 0
        for v in vals:
            try:
                num = int(v[len(prefix):])
                if num > max_num:
                    max_num = num
            except Exception:
                continue
        next_num = max_num + 1
        return f"{prefix}{str(next_num).zfill(3)}"

    def save(self, *args, **kwargs):
        # Ensure a live_appointment_number exists
        if not self.live_appointment_number:
            # Try generating until unique (guard against rare collisions)
            for _ in range(5):
                candidate = self.generate_live_appointment_number()
                if not LiveAppointment.objects.filter(live_appointment_number=candidate).exists():
                    self.live_appointment_number = candidate
                    break
        super().save(*args, **kwargs)

class Prescription(models.Model):
    """Prescription linked to a live appointment"""
    prescription_id = models.AutoField(primary_key=True)
    live_appointment = models.ForeignKey(
        LiveAppointment,
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    prescription_number = models.CharField(max_length=50, unique=True)
    
    # Prescription details
    medicines = models.JSONField(default=list)  # List of medicine objects
    instructions = models.TextField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_instructions = models.TextField(null=True, blank=True)
    
    # Digital signature
    doctor_signature = models.TextField(null=True, blank=True)  # Base64 encoded signature
    signature_date = models.DateTimeField(null=True, blank=True)
    
    # Prescription file (PDF, image, etc. uploaded by doctor)
    prescription_file = models.FileField(upload_to='prescriptions/', null=True, blank=True)
    # Direct reference to the prescribing doctor for easier queries
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_made',
        db_column='doctor_id',
        to_field='doctor_id'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('signed', 'Signed'),
            ('printed', 'Printed'),
            ('cancelled', 'Cancelled')
        ],
        default='draft'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prescription #{self.prescription_number} - {self.live_appointment.appointment.patient.get_full_name()}"
    
    def generate_prescription_number(self):
        """Generate unique prescription number.
        Reverted to original RX-prefixed UUID-based identifier to match
        existing prescription numbers (e.g. RX3E6ACC9F).
        """
        import uuid
        return f"RX{str(uuid.uuid4())[:8].upper()}"
    
    def save(self, *args, **kwargs):
        if not self.prescription_number:
            self.prescription_number = self.generate_prescription_number()
        super().save(*args, **kwargs)


class BookedService(models.Model):
    booking_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='booked_services',
        db_column='user_id',
        to_field='user_id'
    )
    service_name = models.CharField(max_length=150)
    booking_date = models.DateField()
    booking_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Confirmed', 'Confirmed'),
            ('Completed', 'Completed'),
            ('Cancelled', 'Cancelled')
        ],
        default='Pending'
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'booked_services'
        ordering = ['-booking_date', '-booking_time']

    def __str__(self):
        return f"{self.service_name} on {self.booking_date} at {self.booking_time} - {self.user.username}"


class RolePermission(models.Model):
    """Model to store role permission settings"""
    permission_id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, unique=True, choices=[
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('lab_tech', 'Lab Technician'),
        ('patient', 'Patient')
    ])
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'role_permissions'
        ordering = ['role']

    def __str__(self):
        return f"{self.role}: {'Enabled' if self.is_enabled else 'Disabled'}"
