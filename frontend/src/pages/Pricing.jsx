import { useEffect, useState } from "react";
import api from "../api";
import styles from "../styles/Pricing.module.css";

const formatMoney = (value) => {
  const amount = Number(value || 0);

  return amount.toLocaleString("en-UG", {
    maximumFractionDigits: 0,
  });
};

export default function Pricing() {
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);

  const [billingCycle, setBillingCycle] = useState("monthly");
  const [email, setEmail] = useState("");

  const [loading, setLoading] = useState(true);
  const [loadingPlan, setLoadingPlan] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const loadPricingData = async () => {
      setLoading(true);
      setError("");

      try {
        const [plansResponse, subscriptionResponse] =
          await Promise.all([
            api.get("/api/plans/"),
            api.get("/api/subscription/"),
          ]);

        setPlans(plansResponse.data || []);
        setCurrentSubscription(
          subscriptionResponse.data || null
        );

        if (subscriptionResponse.data?.billing_cycle) {
          setBillingCycle(
            subscriptionResponse.data.billing_cycle
          );
        }
      } catch (err) {
        console.error(
          "Unable to load pricing data:",
          err
        );

        setError(
          err.response?.data?.detail ||
            "Unable to load subscription plans."
        );
      } finally {
        setLoading(false);
      }
    };

    loadPricingData();
  }, []);

  const choosePlan = async (planId) => {
    setMessage("");
    setError("");

    if (!planId) {
      setError("Please select a valid subscription plan.");
      return;
    }

    if (planId === "free") {
      setMessage(
        "The Free plan does not require a payment."
      );
      return;
    }

    if (!email.trim()) {
      setError(
        "Please enter your billing email before continuing."
      );
      return;
    }

    setLoadingPlan(planId);

    try {
      const response = await api.post(
        "/api/payments/create/",
        {
          plan: planId,
          billing_cycle: billingCycle,
          email: email.trim(),
        }
      );

      const checkoutUrl =
        response.data?.checkout_url;

      if (!checkoutUrl) {
        throw new Error(
          "The payment provider did not return a checkout URL."
        );
      }

      /*
       * Redirect the customer to Flutterwave's
       * hosted checkout page.
       */
      window.location.assign(checkoutUrl);
    } catch (err) {
      console.error(
        "Payment initialization failed:",
        err
      );

      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to start the payment. Please try again."
      );

      setLoadingPlan("");
    }
  };

  const isCurrentPlan = (planId) => {
    return currentSubscription?.plan === planId;
  };

  const getPlanPrice = (plan) => {
    if (billingCycle === "annual") {
      return (
        plan.price_annual ??
        plan.annual_price ??
        plan.annual ??
        0
      );
    }

    return (
      plan.price_monthly ??
      plan.monthly_price ??
      plan.monthly ??
      0
    );
  };

  const getVehicleLimit = (plan) => {
    return (
      plan.max_vehicles ??
      plan.vehicle_limit ??
      plan.maxVehicles ??
      0
    );
  };

  const getPlanName = (plan) => {
    return (
      plan.name ||
      plan.title ||
      plan.id
        ?.charAt(0)
        .toUpperCase() +
        plan.id?.slice(1) ||
      "Plan"
    );
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          Loading subscription plans...
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>
          Fleet Tracker SaaS
        </p>

        <h1>Choose the right plan for your fleet</h1>

        <p>
          Manage vehicles, income, expenses and fleet
          profitability from one place.
        </p>

        <div className={styles.billingSection}>
          <button
            type="button"
            className={
              billingCycle === "monthly"
                ? styles.active
                : ""
            }
            onClick={() =>
              setBillingCycle("monthly")
            }
          >
            Monthly
          </button>

          <button
            type="button"
            className={
              billingCycle === "annual"
                ? styles.active
                : ""
            }
            onClick={() =>
              setBillingCycle("annual")
            }
          >
            Annual
          </button>
        </div>

        <div className={styles.emailWrapper}>
          <label htmlFor="billing-email">
            Billing email
          </label>

          <input
            id="billing-email"
            type="email"
            value={email}
            placeholder="you@example.com"
            onChange={(event) =>
              setEmail(event.target.value)
            }
          />
        </div>
      </header>

      {error && (
        <div
          className={styles.error}
          role="alert"
        >
          {error}
        </div>
      )}

      {message && (
        <div
          className={styles.message}
          role="status"
        >
          {message}
        </div>
      )}

      {plans.length === 0 ? (
        <div className={styles.empty}>
          No subscription plans are currently available.
        </div>
      ) : (
        <section className={styles.grid}>
          {plans.map((plan) => {
            const planId = plan.id;
            const planName = getPlanName(plan);
            const price = getPlanPrice(plan);
            const vehicleLimit =
              getVehicleLimit(plan);

            const current = isCurrentPlan(planId);
            const processing =
              loadingPlan === planId;

            return (
              <article
                key={planId}
                className={`${styles.card} ${
                  current ? styles.current : ""
                }`}
              >
                {current && (
                  <div className={styles.currentBadge}>
                    Current plan
                  </div>
                )}

                <h2>{planName}</h2>

                <div className={styles.price}>
                  <span>UGX</span>{" "}
                  {formatMoney(price)}

                  <small>
                    /
                    {billingCycle === "annual"
                      ? "year"
                      : "month"}
                  </small>
                </div>

                <div className={styles.vehicleLimit}>
                  Up to{" "}
                  <strong>
                    {vehicleLimit}
                  </strong>{" "}
                  vehicles
                </div>

                <ul className={styles.features}>
                  <li>
                    Fleet dashboard
                  </li>

                  <li>
                    Vehicle management
                  </li>

                  <li>
                    Income tracking
                  </li>

                  <li>
                    Consolidated expenses
                  </li>

                  <li>
                    Profit tracking
                  </li>

                  <li>
                    Fleet reports
                  </li>
                </ul>

                <button
                  type="button"
                  className={styles.planButton}
                  disabled={
                    current || processing
                  }
                  onClick={() =>
                    choosePlan(planId)
                  }
                >
                  {current
                    ? "Current plan"
                    : processing
                      ? "Starting payment..."
                      : planId === "free"
                        ? "Use Free plan"
                        : `Choose ${planName}`}
                </button>
              </article>
            );
          })}
        </section>
      )}

      <section className={styles.paymentInfo}>
        <h3>Secure payments</h3>

        <p>
          Payments are securely processed through
          Flutterwave. You can pay using supported
          card and Uganda mobile money options.
        </p>

        <p>
          Your Fleet Tracker subscription is activated
          only after the payment has been verified by
          our server.
        </p>
      </section>
    </div>
  );
}