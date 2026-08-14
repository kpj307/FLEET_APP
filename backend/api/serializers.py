from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework import serializers

from .models import Expense, Income, Organization, Subscription, Vehicle
from .services import PLAN_LIMITS, create_owner_organization


class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(
        write_only=True,
        max_length=255,
        required=True,
    )

    class Meta:
        model = User
        fields = ["id", "username", "password", "business_name"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        business_name = validated_data.pop("business_name")
        user = User.objects.create_user(**validated_data)
        create_owner_organization(user, business_name)
        return user


class OrganizationSerializer(serializers.ModelSerializer):
    plan = serializers.CharField(
        source="subscription.plan",
        read_only=True,
    )
    subscription_status = serializers.CharField(
        source="subscription.status",
        read_only=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "currency",
            "timezone",
            "plan",
            "subscription_status",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "plan",
            "subscription_status",
            "created_at",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Business name is required."
            )
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.SerializerMethodField()
    max_vehicles = serializers.SerializerMethodField()
    price_monthly = serializers.SerializerMethodField()
    price_annual = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "plan",
            "status",
            "billing_cycle",
            "started_at",
            "expires_at",
            "vehicle_count",
            "max_vehicles",
            "price_monthly",
            "price_annual",
        ]
        read_only_fields = [
            "status",
            "started_at",
            "expires_at",
            "vehicle_count",
            "max_vehicles",
            "price_monthly",
            "price_annual",
        ]

    def get_vehicle_count(self, obj):
        return obj.organization.vehicles.count()

    def get_max_vehicles(self, obj):
        return PLAN_LIMITS[obj.plan]["max_vehicles"]

    def get_price_monthly(self, obj):
        return PLAN_LIMITS[obj.plan]["price_monthly"]

    def get_price_annual(self, obj):
        return PLAN_LIMITS[obj.plan]["price_annual"]


class VehicleSerializer(serializers.ModelSerializer):
    total_income = serializers.SerializerMethodField()
    total_expense = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "make",
            "plate",
            "created_at",
            "total_income",
            "total_expense",
            "profit",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "total_income",
            "total_expense",
            "profit",
        ]

    def validate_plate(self, value):
        value = value.strip().upper()
        organization = self.context["request"].user.organization

        query = Vehicle.objects.filter(
            organization=organization,
            plate__iexact=value,
        )

        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError(
                "A vehicle with this plate already exists."
            )

        return value

    def validate_make(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Vehicle make is required."
            )
        return value

    def _date_filters(self):
        request = self.context.get("request")
        if not request:
            return {}

        period = request.query_params.get("period")
        start_raw = request.query_params.get("start")
        end_raw = request.query_params.get("end")

        start = parse_date(start_raw) if start_raw else None
        end = parse_date(end_raw) if end_raw else None

        if (start_raw and not start) or (end_raw and not end):
            raise serializers.ValidationError(
                {"date": "Dates must use YYYY-MM-DD format."}
            )

        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    {"date": "Start date cannot be after end date."}
                )
            return {"date__range": [start, end]}

        today = date.today()

        if period == "weekly":
            week_start = today - timedelta(days=today.weekday())
            return {"date__range": [week_start, today]}

        if period == "monthly":
            return {
                "date__gte": today.replace(day=1),
                "date__lte": today,
            }

        if period == "annually":
            return {
                "date__range": [
                    date(today.year, 1, 1),
                    today,
                ]
            }

        return {}

    def _total(self, model, vehicle):
        return (
            model.objects.filter(
                vehicle=vehicle,
                **self._date_filters(),
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

    def get_total_income(self, obj):
        return self._total(Income, obj)

    def get_total_expense(self, obj):
        return self._total(Expense, obj)

    def get_profit(self, obj):
        return self.get_total_income(obj) - self.get_total_expense(obj)


class IncomeSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(
        source="vehicle.plate",
        read_only=True,
    )

    class Meta:
        model = Income
        fields = [
            "id",
            "vehicle",
            "vehicle_plate",
            "amount",
            "date",
            "description",
        ]
        extra_kwargs = {
            "date": {"required": False},
        }

    def validate_vehicle(self, vehicle):
        organization = self.context["request"].user.organization

        if vehicle.organization_id != organization.id:
            raise serializers.ValidationError(
                "Invalid vehicle."
            )

        return vehicle

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(
        source="vehicle.plate",
        read_only=True,
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "vehicle",
            "vehicle_plate",
            "amount",
            "date",
            "description",
            "category",
        ]
        extra_kwargs = {
            "date": {"required": False},
        }

    def validate_vehicle(self, vehicle):
        organization = self.context["request"].user.organization

        if vehicle.organization_id != organization.id:
            raise serializers.ValidationError(
                "Invalid vehicle."
            )

        return vehicle

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )
        return value
