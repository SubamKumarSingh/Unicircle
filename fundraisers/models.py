from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.urls import reverse

User = settings.AUTH_USER_MODEL

class Fundraiser(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fundraisers")
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="fundraisers/images/", null=True, blank=True)
    goal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("1.00"))])
    raised = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    donors_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False) 
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("fundraisers:detail", args=[self.pk])

    @property
    def progress_percent(self):
        try:
            return min(100, int((self.raised / self.goal) * 100))
        except Exception:
            return 0


class Donation(models.Model):
    PAYMENT_OFFLINE = "offline"   # e.g. bank transfer, cash
    PAYMENT_EXTERNAL = "external" # external gateway like Razorpay, PayU (placeholder)
    PAYMENT_CARD = "card"         # card via a gateway (Stripe, etc.) -- currently placeholder

    PAYMENT_CHOICES = [
        (PAYMENT_OFFLINE, "Offline / Manual"),
        (PAYMENT_EXTERNAL, "External Gateway"),
        (PAYMENT_CARD, "Card (gateway)"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    fundraiser = models.ForeignKey(Fundraiser, on_delete=models.CASCADE, related_name="donations")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("1.00"))])
    currency = models.CharField(max_length=8, default="INR")
    payment_method = models.CharField(max_length=32, choices=PAYMENT_CHOICES, default=PAYMENT_OFFLINE)
    stripe_session_id = models.CharField(max_length=128, blank=True, null=True)
    stripe_payment_intent = models.CharField(max_length=128, blank=True, null=True)
    stripe_payment_status = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference = models.CharField(max_length=255, blank=True, null=True)  # external gateway reference / txn id
    metadata = models.JSONField(default=dict, blank=True)  # any extra info (safe to add later)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.fundraiser} — ₹{self.amount} ({self.status})"

    def mark_succeeded(self):
        """Mark donation succeeded and update fundraiser totals atomically."""
        if self.status == self.STATUS_SUCCEEDED:
            return
        self.status = self.STATUS_SUCCEEDED
        with transaction.atomic():
            self.save(update_fields=["status"])
            f = Fundraiser.objects.select_for_update().get(pk=self.fundraiser_id)
            f.raised = (f.raised or Decimal("0.00")) + self.amount
            f.donors_count = (f.donors_count or 0) + 1
            f.save(update_fields=["raised", "donors_count"])
