from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.utils.dateparse import parse_date

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expense, Income, Organization, Vehicle
from .serializers import (
    ExpenseSerializer,
    IncomeSerializer,
    OrganizationSerializer,
    SubscriptionSerializer,
    UserSerializer,
    VehicleSerializer,
)
from .services import PLAN_LIMITS, can_add_vehicle
from .throttles import RegistrationThrottle


def apply_date_range(queryset, start_raw=None, end_raw=None, period=None):
    if not start_raw and not end_raw and period:
        from datetime import date, timedelta

        today = date.today()

        if period == "weekly":
            start_raw = (
                today - timedelta(days=today.weekday())
            ).isoformat()
            end_raw = today.isoformat()

        elif period == "monthly":
            start_raw = today.replace(day=1).isoformat()
            end_raw = today.isoformat()

        elif period == "annually":
            start_raw = date(today.year, 1, 1).isoformat()
            end_raw = today.isoformat()

    if start_raw or end_raw:
        start = parse_date(start_raw) if start_raw else None
        end = parse_date(end_raw) if end_raw else None

        if (start_raw and not start) or (end_raw and not end):
            raise ValidationError(
                {"date": "Dates must use YYYY-MM-DD format."}
            )

        if start and end and start > end:
            raise ValidationError(
                {"date": "Start date cannot be after end date."}
            )

        if start:
            queryset = queryset.filter(date__gte=start)

        if end:
            queryset = queryset.filter(date__lte=end)

    return queryset


class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    throttle_classes = [
        RegistrationThrottle,
    ]

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

class OrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = request.user.organization

        return Response(
            OrganizationSerializer(organization).data
        )

    def patch(self, request):
        organization = request.user.organization

        serializer = OrganizationSerializer(
            organization,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data
        )

class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = (
            request.user.organization.subscription
        )

        subscription.refresh_status()

        return Response(
            SubscriptionSerializer(subscription).data
        )

    def patch(self, request):
        raise ValidationError(
            {
                "detail": (
                    "Subscription changes must be completed "
                    "through the payment process."
                )
            }
        )

class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            [
                {
                    "id": plan,
                    "name": plan.title(),
                    **values,
                }
                for plan, values in PLAN_LIMITS.items()
            ]
        )


class VehicleListCreate(generics.ListCreateAPIView):
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(
            organization=self.request.user.organization
        )

    def perform_create(self, serializer):
        organization = self.request.user.organization

        if not can_add_vehicle(organization):
            raise ValidationError(
                {
                    "plan": (
                        "Vehicle limit reached. "
                        "Upgrade your plan to add another vehicle."
                    )
                }
            )

        serializer.save(organization=organization)


class VehicleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(
            organization=self.request.user.organization
        )


class IncomeListCreateView(generics.ListCreateAPIView):
    serializer_class = IncomeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Income.objects.filter(
            vehicle__organization=self.request.user.organization
        ).select_related("vehicle")

        vehicle_id = self.request.query_params.get("vehicle")

        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        return apply_date_range(
            queryset,
            self.request.query_params.get("start"),
            self.request.query_params.get("end"),
            self.request.query_params.get("period"),
        )


class IncomeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IncomeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Income.objects.filter(
            vehicle__organization=self.request.user.organization
        ).select_related("vehicle")


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Expense.objects.filter(
            vehicle__organization=self.request.user.organization
        ).select_related("vehicle")

        vehicle_id = self.request.query_params.get("vehicle")
        category = self.request.query_params.get("category")

        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        if category:
            queryset = queryset.filter(category=category)

        return apply_date_range(
            queryset,
            self.request.query_params.get("start"),
            self.request.query_params.get("end"),
            self.request.query_params.get("period"),
        )


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(
            vehicle__organization=self.request.user.organization
        ).select_related("vehicle")


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization = request.user.organization

        subscription = organization.subscription
        subscription.refresh_status()

        incomes = Income.objects.filter(
            vehicle__organization=organization
        )
        expenses = Expense.objects.filter(
            vehicle__organization=organization
        )

        incomes = apply_date_range(
            incomes,
            request.query_params.get("start"),
            request.query_params.get("end"),
            request.query_params.get("period"),
        )
        expenses = apply_date_range(
            expenses,
            request.query_params.get("start"),
            request.query_params.get("end"),
            request.query_params.get("period"),
        )

        total_income = incomes.aggregate(
            total=Sum("amount")
        )["total"] or 0

        total_expense = expenses.aggregate(
            total=Sum("amount")
        )["total"] or 0

        breakdown = list(
            expenses.values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        return Response(
            {
                "organization": organization.name,
                "vehicle_count": organization.vehicles.count(),
                "income": total_income,
                "expenses": total_expense,
                "profit": total_income - total_expense,
                "expense_breakdown": breakdown,
                "plan": subscription.plan,
            }
        )
