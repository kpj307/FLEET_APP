from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Expense, Income, Organization, Subscription, Vehicle


class OwnerSaaSTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="joe",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="other",
            password="StrongPass123!",
        )

        self.organization = Organization.objects.create(
            owner=self.user,
            name="Joe Transport",
            slug="joe-transport",
        )
        Subscription.objects.create(
            organization=self.organization,
            plan="free",
        )

        self.other_organization = Organization.objects.create(
            owner=self.other,
            name="Other Transport",
            slug="other-transport",
        )
        Subscription.objects.create(
            organization=self.other_organization,
            plan="free",
        )

        self.vehicle = Vehicle.objects.create(
            organization=self.organization,
            plate="UBA123A",
            make="Toyota",
        )
        self.other_vehicle = Vehicle.objects.create(
            organization=self.other_organization,
            plate="UBB456B",
            make="Ford",
        )

        self.client.force_authenticate(self.user)

    def test_registration_creates_owner_organization(self):
        response = self.client.post(
            "/api/user/register/",
            {
                "username": "new-owner",
                "password": "StrongPass123!",
                "business_name": "New Fleet Ltd",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(username="new-owner")
        self.assertEqual(
            user.organization.name,
            "New Fleet Ltd",
        )
        self.assertEqual(
            user.organization.subscription.plan,
            "free",
        )

    def test_vehicle_list_is_tenant_scoped(self):
        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["plate"], "UBA123A")

    def test_cross_tenant_income_is_rejected(self):
        response = self.client.post(
            "/api/income/",
            {
                "vehicle": self.other_vehicle.id,
                "amount": "100000",
                "date": "2026-08-01",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_cross_tenant_expense_is_rejected(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "vehicle": self.other_vehicle.id,
                "amount": "100000",
                "category": "Fuel",
                "date": "2026-08-01",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_cross_tenant_vehicle_detail_is_not_visible(self):
        response = self.client.get(
            f"/api/vehicles/{self.other_vehicle.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_free_plan_has_three_vehicle_limit(self):
        Vehicle.objects.create(
            organization=self.organization,
            plate="UBC111C",
            make="Isuzu",
        )
        Vehicle.objects.create(
            organization=self.organization,
            plate="UBD222D",
            make="Nissan",
        )

        response = self.client.post(
            "/api/vehicles/",
            {
                "plate": "UBE333E",
                "make": "Mercedes",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_dashboard_is_tenant_scoped(self):
        Income.objects.create(
            vehicle=self.vehicle,
            amount="1000000",
            date="2026-08-01",
        )
        Expense.objects.create(
            vehicle=self.vehicle,
            amount="300000",
            category="Fuel",
            date="2026-08-01",
        )
        Income.objects.create(
            vehicle=self.other_vehicle,
            amount="9000000",
            date="2026-08-01",
        )

        response = self.client.get(
            "/api/dashboard/",
            {"start": "2026-08-01", "end": "2026-08-31"},
        )

        self.assertEqual(
            float(response.data["income"]),
            1000000.00,
        )

        self.assertEqual(
            float(response.data["expenses"]),
            300000.00,
        )

        self.assertEqual(
            float(response.data["profit"]),
            700000.00,
        )

    def test_owner_can_change_subscription_plan(self):
        response = self.client.patch(
            "/api/subscription/",
            {
                "plan": "business",
                "billing_cycle": "monthly",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], "business")

    def test_owner_can_update_organization(self):
        response = self.client.patch(
            "/api/organization/",
            {"name": "Updated Transport"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["name"],
            "Updated Transport",
        )
