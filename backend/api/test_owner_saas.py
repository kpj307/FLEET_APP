from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Expense, Income, Organization, Subscription, Vehicle


class OwnerSaaSDataIsolationTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="StrongPass123!",
        )

        self.other_owner = User.objects.create_user(
            username="other-owner",
            password="StrongPass123!",
        )

        self.org = Organization.objects.create(
            owner=self.owner,
            name="Owner Fleet",
            slug="owner-fleet",
        )

        Subscription.objects.create(
            organization=self.org,
            plan="business",
        )

        self.other_org = Organization.objects.create(
            owner=self.other_owner,
            name="Other Fleet",
            slug="other-fleet",
        )

        Subscription.objects.create(
            organization=self.other_org,
            plan="business",
        )

        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            plate="UBA100A",
            make="Toyota",
        )

        self.second_vehicle = Vehicle.objects.create(
            organization=self.org,
            plate="UBA200A",
            make="Isuzu",
        )

        self.other_vehicle = Vehicle.objects.create(
            organization=self.other_org,
            plate="UBB100B",
            make="Ford",
        )

        self.income = Income.objects.create(
            vehicle=self.vehicle,
            amount=Decimal("1000000.00"),
            description="Owner revenue",
            date="2026-08-05",
        )

        self.other_income = Income.objects.create(
            vehicle=self.other_vehicle,
            amount=Decimal("9000000.00"),
            description="Other revenue",
            date="2026-08-05",
        )

        self.expense = Expense.objects.create(
            vehicle=self.vehicle,
            amount=Decimal("300000.00"),
            category="Fuel",
            description="Owner fuel",
            date="2026-08-06",
        )

        self.other_expense = Expense.objects.create(
            vehicle=self.other_vehicle,
            amount=Decimal("8000000.00"),
            category="Fuel",
            description="Other fuel",
            date="2026-08-06",
        )

        self.client.force_authenticate(self.owner)

    # ---------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------

    def test_unauthenticated_users_cannot_access_fleet_data(self):
        self.client.force_authenticate(user=None)

        for endpoint in (
            "/api/vehicles/",
            "/api/income/",
            "/api/expenses/",
        ):
            response = self.client.get(endpoint)

            self.assertIn(
                response.status_code,
                (
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN,
                ),
            )

    # ---------------------------------------------------------
    # Vehicles
    # ---------------------------------------------------------

    def test_vehicle_list_is_tenant_scoped(self):
        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, 200)

        plates = {
            vehicle["plate"]
            for vehicle in response.data
        }

        self.assertEqual(
            plates,
            {"UBA100A", "UBA200A"},
        )

        self.assertNotIn("UBB100B", plates)

    def test_owner_can_create_vehicle(self):
        response = self.client.post(
            "/api/vehicles/",
            {
                "plate": "UBA300A",
                "make": "Nissan",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        vehicle = Vehicle.objects.get(
            plate="UBA300A"
        )

        self.assertEqual(
            vehicle.organization_id,
            self.org.id,
        )

    def test_owner_can_retrieve_vehicle(self):
        response = self.client.get(
            f"/api/vehicles/{self.vehicle.id}/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["plate"],
            "UBA100A",
        )

    def test_owner_cannot_retrieve_foreign_vehicle(self):
        response = self.client.get(
            f"/api/vehicles/{self.other_vehicle.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_owner_can_update_vehicle(self):
        response = self.client.patch(
            f"/api/vehicles/{self.vehicle.id}/",
            {
                "make": "Toyota Hilux",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.vehicle.refresh_from_db()

        self.assertEqual(
            self.vehicle.make,
            "Toyota Hilux",
        )

    def test_owner_cannot_update_foreign_vehicle(self):
        response = self.client.patch(
            f"/api/vehicles/{self.other_vehicle.id}/",
            {
                "make": "Changed",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.other_vehicle.refresh_from_db()

        self.assertEqual(
            self.other_vehicle.make,
            "Ford",
        )

    def test_owner_can_delete_vehicle(self):
        vehicle_id = self.second_vehicle.id

        response = self.client.delete(
            f"/api/vehicles/{vehicle_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Vehicle.objects.filter(
                id=vehicle_id
            ).exists()
        )

    def test_owner_cannot_delete_foreign_vehicle(self):
        response = self.client.delete(
            f"/api/vehicles/{self.other_vehicle.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertTrue(
            Vehicle.objects.filter(
                id=self.other_vehicle.id
            ).exists()
        )

    def test_duplicate_plate_is_rejected_within_organization(self):
        response = self.client.post(
            "/api/vehicles/",
            {
                "plate": "uba100a",
                "make": "Another Toyota",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_same_plate_can_exist_in_different_organizations(self):
        self.client.force_authenticate(
            self.other_owner
        )

        response = self.client.post(
            "/api/vehicles/",
            {
                "plate": "UBA100A",
                "make": "Another Toyota",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    # ---------------------------------------------------------
    # Income
    # ---------------------------------------------------------

    def test_income_list_is_tenant_scoped(self):
        response = self.client.get("/api/income/")

        self.assertEqual(response.status_code, 200)

        ids = {
            income["id"]
            for income in response.data
        }

        self.assertIn(
            self.income.id,
            ids,
        )

        self.assertNotIn(
            self.other_income.id,
            ids,
        )

    def test_owner_can_create_income(self):
        response = self.client.post(
            "/api/income/",
            {
                "vehicle": self.second_vehicle.id,
                "amount": "250000",
                "description": "Trip revenue",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        income = Income.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            income.vehicle.organization_id,
            self.org.id,
        )

    def test_owner_cannot_create_income_for_foreign_vehicle(self):
        response = self.client.post(
            "/api/income/",
            {
                "vehicle": self.other_vehicle.id,
                "amount": "250000",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_owner_cannot_update_foreign_income(self):
        response = self.client.patch(
            f"/api/income/{self.other_income.id}/",
            {
                "amount": "1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_owner_cannot_delete_foreign_income(self):
        response = self.client.delete(
            f"/api/income/{self.other_income.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_income_rejects_zero_amount(self):
        response = self.client.post(
            "/api/income/",
            {
                "vehicle": self.vehicle.id,
                "amount": "0",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_income_rejects_negative_amount(self):
        response = self.client.post(
            "/api/income/",
            {
                "vehicle": self.vehicle.id,
                "amount": "-10",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ---------------------------------------------------------
    # Expenses
    # ---------------------------------------------------------

    def test_expense_list_is_tenant_scoped(self):
        response = self.client.get("/api/expenses/")

        self.assertEqual(response.status_code, 200)

        ids = {
            expense["id"]
            for expense in response.data
        }

        self.assertIn(
            self.expense.id,
            ids,
        )

        self.assertNotIn(
            self.other_expense.id,
            ids,
        )

    def test_owner_can_create_expense(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "vehicle": self.vehicle.id,
                "amount": "150000",
                "category": "Maintenance",
                "description": "Oil change",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_owner_cannot_create_expense_for_foreign_vehicle(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "vehicle": self.other_vehicle.id,
                "amount": "150000",
                "category": "Maintenance",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_owner_cannot_update_foreign_expense(self):
        response = self.client.patch(
            f"/api/expenses/{self.other_expense.id}/",
            {
                "amount": "1",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_owner_cannot_delete_foreign_expense(self):
        response = self.client.delete(
            f"/api/expenses/{self.other_expense.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_expense_rejects_zero_amount(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "vehicle": self.vehicle.id,
                "amount": "0",
                "category": "Fuel",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_expense_rejects_negative_amount(self):
        response = self.client.post(
            "/api/expenses/",
            {
                "vehicle": self.vehicle.id,
                "amount": "-1",
                "category": "Fuel",
                "date": "2026-08-07",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ---------------------------------------------------------
    # Filters
    # ---------------------------------------------------------

    def test_income_vehicle_filter(self):
        second_income = Income.objects.create(
            vehicle=self.second_vehicle,
            amount=Decimal("500000"),
            date="2026-08-08",
        )

        response = self.client.get(
            "/api/income/",
            {
                "vehicle": self.second_vehicle.id
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {
                item["id"]
                for item in response.data
            },
            {second_income.id},
        )

    def test_expense_vehicle_filter(self):
        second_expense = Expense.objects.create(
            vehicle=self.second_vehicle,
            amount=Decimal("70000"),
            category="Fuel",
            date="2026-08-08",
        )

        response = self.client.get(
            "/api/expenses/",
            {
                "vehicle": self.second_vehicle.id
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {
                item["id"]
                for item in response.data
            },
            {second_expense.id},
        )

    def test_expense_category_filter(self):
        Expense.objects.create(
            vehicle=self.vehicle,
            amount=Decimal("90000"),
            category="Maintenance",
            date="2026-08-08",
        )

        response = self.client.get(
            "/api/expenses/",
            {
                "category": "Maintenance"
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            all(
                item["category"] == "Maintenance"
                for item in response.data
            )
        )

    # ---------------------------------------------------------
    # Dashboard
    # ---------------------------------------------------------

    def test_dashboard_is_tenant_scoped(self):
        response = self.client.get(
            "/api/dashboard/",
            {
                "start": "2026-08-01",
                "end": "2026-08-31",
            },
        )

        self.assertEqual(response.status_code, 200)

        # Compare numeric values, not Decimal formatting.
        self.assertEqual(
            Decimal(str(response.data["income"])),
            Decimal("1000000"),
        )

        self.assertEqual(
            Decimal(str(response.data["expenses"])),
            Decimal("300000"),
        )

        self.assertEqual(
            Decimal(str(response.data["profit"])),
            Decimal("700000"),
        )

    def test_dashboard_date_filter_excludes_old_records(self):
        Income.objects.create(
            vehicle=self.vehicle,
            amount=Decimal("200000"),
            date="2026-07-01",
        )

        Expense.objects.create(
            vehicle=self.vehicle,
            amount=Decimal("50000"),
            category="Fuel",
            date="2026-07-02",
        )

        response = self.client.get(
            "/api/dashboard/",
            {
                "start": "2026-08-01",
                "end": "2026-08-31",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Decimal(str(response.data["income"])),
            Decimal("1000000"),
        )

        self.assertEqual(
            Decimal(str(response.data["expenses"])),
            Decimal("300000"),
        )

    def test_vehicle_financial_totals(self):
        response = self.client.get("/api/vehicles/")

        self.assertEqual(response.status_code, 200)

        vehicle = next(
            item
            for item in response.data
            if item["id"] == self.vehicle.id
        )

        self.assertEqual(
            Decimal(str(vehicle["total_income"])),
            Decimal("1000000"),
        )

        self.assertEqual(
            Decimal(str(vehicle["total_expense"])),
            Decimal("300000"),
        )

        self.assertEqual(
            Decimal(str(vehicle["profit"])),
            Decimal("700000"),
        )


class OwnerSaaSSubscriptionTests(APITestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="subscription-owner",
            password="StrongPass123!",
        )

        self.organization = Organization.objects.create(
            owner=self.owner,
            name="Subscription Fleet",
            slug="subscription-fleet",
        )

        Subscription.objects.create(
            organization=self.organization,
            plan="free",
        )

        self.client.force_authenticate(self.owner)

    def test_organization_endpoint(self):
        response = self.client.get(
            "/api/organization/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["name"],
            "Subscription Fleet",
        )

        self.assertEqual(
            response.data["plan"],
            "free",
        )

    def test_owner_can_update_organization(self):
        response = self.client.patch(
            "/api/organization/",
            {
                "name": "Updated Fleet",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
            response.data,
        )

        self.organization.refresh_from_db()

        self.assertEqual(
            self.organization.name,
            "Updated Fleet",
        )

    def test_plan_list(self):
        response = self.client.get(
            "/api/plans/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            {
                item["id"]
                for item in response.data
            },
            {
                "free",
                "starter",
                "business",
                "professional",
            },
        )

    def test_owner_cannot_change_subscription_directly(self):
        response = self.client.patch(
            "/api/subscription/",
            {
                "plan": "business",
                "billing_cycle": "annual",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.organization.subscription.refresh_from_db()

        self.assertEqual(
            self.organization.subscription.plan,
            "free",
        )

    def test_invalid_subscription_plan_is_rejected(self):
        response = self.client.patch(
            "/api/subscription/",
            {
                "plan": "enterprise",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_expired_paid_subscription_falls_back_to_free(self):
        from datetime import timedelta
        from django.utils.timezone import now

        subscription = self.organization.subscription

        subscription.plan = "professional"
        subscription.status = "active"
        subscription.billing_cycle = "monthly"
        subscription.expires_at = (
            now() - timedelta(days=1)
        )
        subscription.save()

        response = self.client.get(
            "/api/subscription/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["plan"],
            "free",
        )

        subscription.refresh_from_db()

        self.assertEqual(
            subscription.plan,
            "free",
        )

        self.assertEqual(
            subscription.status,
            "active",
        )

        self.assertIsNone(
            subscription.expires_at
        )

    def test_active_paid_subscription_remains_active(self):
        from datetime import timedelta
        from django.utils.timezone import now

        subscription = self.organization.subscription

        subscription.plan = "business"
        subscription.status = "active"
        subscription.billing_cycle = "monthly"
        subscription.expires_at = (
            now() + timedelta(days=30)
        )
        subscription.save()

        response = self.client.get(
            "/api/subscription/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["plan"],
            "business",
        )

        subscription.refresh_from_db()

        self.assertEqual(
            subscription.plan,
            "business",
        )

    def test_expired_subscription_uses_free_vehicle_limit(self):
        from datetime import timedelta
        from django.utils.timezone import now

        subscription = self.organization.subscription

        subscription.plan = "starter"
        subscription.status = "active"
        subscription.billing_cycle = "monthly"
        subscription.expires_at = (
            now() - timedelta(days=1)
        )
        subscription.save()

        # Free plan allows 3 vehicles.
        Vehicle.objects.create(
            organization=self.organization,
            plate="UBA301A",
            make="Toyota",
        )

        Vehicle.objects.create(
            organization=self.organization,
            plate="UBA302A",
            make="Toyota",
        )

        Vehicle.objects.create(
            organization=self.organization,
            plate="UBA303A",
            make="Toyota",
        )

        response = self.client.post(
            "/api/vehicles/",
            {
                "plate": "UBA304A",
                "make": "Toyota",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "plan",
            response.data,
        )

    def test_subscription_refresh_status_downgrades_expired_plan(self):
        from datetime import timedelta
        from django.utils.timezone import now

        subscription = self.organization.subscription

        subscription.plan = "professional"
        subscription.status = "active"
        subscription.billing_cycle = "annual"
        subscription.expires_at = (
            now() - timedelta(seconds=1)
        )
        subscription.save()

        subscription.refresh_status()

        self.assertEqual(
            subscription.plan,
            "free",
        )

        self.assertEqual(
            subscription.status,
            "active",
        )

        self.assertEqual(
            subscription.billing_cycle,
            "monthly",
        )

        self.assertIsNone(
            subscription.expires_at
        )