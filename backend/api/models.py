from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.timezone import now


class Organization(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("starter", "Starter"),
        ("business", "Business"),
        ("professional", "Professional"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    currency = models.CharField(max_length=3, default="UGX")
    timezone = models.CharField(max_length=64, default="Africa/Kampala")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past due"),
        ("cancelled", "Cancelled"),
    ]
    BILLING_CHOICES = [
        ("monthly", "Monthly"),
        ("annual", "Annual"),
    ]
    PLAN_PRICES = {
        "free": {
            "monthly": Decimal("0"),
            "annual": Decimal("0"),
            "max_vehicles": 3,
        },
        "starter": {
            "monthly": Decimal("25000"),
            "annual": Decimal("250000"),
            "max_vehicles": 5,
        },
        "business": {
            "monthly": Decimal("75000"),
            "annual": Decimal("750000"),
            "max_vehicles": 25,
        },
        "professional": {
            "monthly": Decimal("150000"),
            "annual": Decimal("1500000"),
            "max_vehicles": 100,
        },
    }

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.CharField(
        max_length=30,
        choices=Organization.PLAN_CHOICES,
        default="free",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="active",
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CHOICES,
        default="monthly",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    external_customer_id = models.CharField(max_length=255, blank=True)
    external_subscription_id = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.organization.name} - {self.plan}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    tx_ref = models.CharField(
        max_length=255,
        unique=True,
    )

    provider_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="UGX",
    )

    plan = models.CharField(
        max_length=30,
    )

    billing_cycle = models.CharField(
        max_length=20,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )

    checkout_url = models.URLField(
        blank=True,
    )

    provider_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]


class Vehicle(models.Model):
    plate = models.CharField(max_length=100, db_index=True)
    make = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )

    class Meta:
        ordering = ["plate"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "plate"],
                name="unique_vehicle_plate_per_organization",
            )
        ]

    def __str__(self):
        return self.plate


class Income(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="incomes",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField(default=now, db_index=True)

    class Meta:
        ordering = ["-date", "-id"]


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("Fuel", "Fuel"),
        ("Maintenance", "Maintenance"),
        ("Repairs", "Repairs"),
        ("Insurance", "Insurance"),
        ("Licensing", "Licensing"),
        ("Salaries", "Salaries"),
        ("Routine", "Routine"),
        ("Other", "Other"),
    ]

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default="Other",
    )
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField(default=now, db_index=True)

    class Meta:
        ordering = ["-date", "-id"]
