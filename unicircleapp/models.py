from django.db import models
from django.conf import settings
# Create your models here.
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPES = [
        ("student", "Student"),
        ("alumni", "Alumni"),
        ("faculty", "Faculty"),
    ]

    email = models.EmailField(unique=True)
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default="student"
    )
    is_approved = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    unapproved_message = models.CharField(max_length=50, blank=True, null=True)
    def __str__(self):
        return f"{self.username} ({self.user_type})"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # ---------- Common fields ----------
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    course = models.CharField(max_length=100, blank=True, null=True)
    year = models.CharField(max_length=20, blank=True, null=True)

    # ---------- Student Specific ----------
    enrollment_number = models.CharField(max_length=50, blank=True, null=True)
    branch = models.CharField(max_length=100, blank=True, null=True)
    semester = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=20, blank=True, null=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)

    # ---------- Alumni Specific ----------
    graduation_year = models.IntegerField(blank=True, null=True)
    higher_studies = models.CharField(max_length=150, blank=True, null=True)
    current_position = models.CharField(max_length=150, blank=True, null=True)
    company = models.CharField(max_length=150, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    achievements = models.TextField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    mentoring_interest = models.BooleanField(default=False)

    # ---------- Faculty Specific ----------
    department = models.CharField(max_length=100, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    specialization = models.CharField(max_length=150, blank=True, null=True)
    classes_taught = models.TextField(blank=True, null=True)
    publications = models.TextField(blank=True, null=True)
    research_interests = models.TextField(blank=True, null=True)
    office_hours = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class RoleUpgradeRequest(models.Model):
    REQUEST_TYPES = [
        ("student", "Continue as Student"),
        ("alumni", "Alumni"),
        ("faculty", "Faculty"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_role = models.CharField(max_length=20, choices=REQUEST_TYPES)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} requests {self.requested_role}"


class Follow(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]

    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('follower', 'followed')

    def __str__(self):
        return f"{self.follower.username} -> {self.followed.username} ({self.status})"