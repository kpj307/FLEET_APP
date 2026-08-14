from django.urls import path

from .payment_views import (
    CreatePaymentView,
    PaymentStatusView,
    FlutterwaveWebhookView,
)

from . import views

urlpatterns = [
    # Existing SaaS endpoints
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("organization/", views.OrganizationView.as_view(), name="organization"),
    path("plans/", views.PlanListView.as_view(), name="plans"),
    path("subscription/", views.SubscriptionView.as_view(), name="subscription"),

    # NEW payment endpoints
    path(
        "payments/create/",
        CreatePaymentView.as_view(),
        name="payment-create",
    ),
    path(
        "payments/status/<str:tx_ref>/",
        PaymentStatusView.as_view(),
        name="payment-status",
    ),
    path(
        "payments/flutterwave/webhook/",
        FlutterwaveWebhookView.as_view(),
        name="flutterwave-webhook",
    ),

    # Existing fleet endpoints
    path("vehicles/", views.VehicleListCreate.as_view(), name="vehicle-list"),
    path(
        "vehicles/<int:pk>/",
        views.VehicleDetailView.as_view(),
        name="vehicle-detail",
    ),

    path("income/", views.IncomeListCreateView.as_view(), name="income-list-create"),
    path("income/<int:pk>/", views.IncomeDetailView.as_view(), name="income-detail"),

    path("expenses/", views.ExpenseListCreateView.as_view(), name="expense-list-create"),
    path("expenses/<int:pk>/", views.ExpenseDetailView.as_view(), name="expense-detail"),
]
