import { useEffect, useState } from "react";
import api from "../api";
import styles from "../styles/SaaSDashboard.module.css";

const money = (value) =>
  Number(value || 0).toLocaleString("en-UG", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [period, setPeriod] = useState("monthly");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");

    try {
      const params = { period };

      const [
        dashboardResponse,
        organizationResponse,
        vehiclesResponse,
      ] = await Promise.all([
        api.get("/api/dashboard/", { params }),
        api.get("/api/organization/"),
        api.get("/api/vehicles/", { params }),
      ]);

      setDashboard(dashboardResponse.data);
      setOrganization(organizationResponse.data);
      setVehicles(vehiclesResponse.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load your fleet dashboard."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [period]);

  if (loading && !dashboard) {
    return <div className={styles.container}>Loading dashboard...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Fleet overview</p>
          <h1>{organization?.name || "Your Fleet"}</h1>
          <p>
            Your fleet revenue, consolidated expenses and
            profitability.
          </p>
        </div>

        <span className={styles.plan}>
          {organization?.plan || "free"} plan
        </span>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.filters}>
        {["weekly", "monthly", "annually"].map((item) => (
          <button
            key={item}
            className={period === item ? styles.active : ""}
            onClick={() => setPeriod(item)}
          >
            {item[0].toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>

      <section className={styles.stats}>
        <article>
          <span>Vehicles</span>
          <strong>{dashboard?.vehicle_count || 0}</strong>
        </article>

        <article>
          <span>Revenue</span>
          <strong>UGX {money(dashboard?.income)}</strong>
        </article>

        <article>
          <span>Expenses</span>
          <strong>UGX {money(dashboard?.expenses)}</strong>
        </article>

        <article>
          <span>Net Profit</span>
          <strong>UGX {money(dashboard?.profit)}</strong>
        </article>
      </section>

      <section className={styles.grid}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2>Fleet performance</h2>
            <p>Income, expenses and profit per vehicle.</p>
          </div>

          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Income</th>
                  <th>Expenses</th>
                  <th>Profit</th>
                </tr>
              </thead>

              <tbody>
                {vehicles.map((vehicle) => (
                  <tr key={vehicle.id}>
                    <td>
                      <strong>{vehicle.plate}</strong>
                      <small>{vehicle.make}</small>
                    </td>
                    <td>UGX {money(vehicle.total_income)}</td>
                    <td>UGX {money(vehicle.total_expense)}</td>
                    <td>UGX {money(vehicle.profit)}</td>
                  </tr>
                ))}

                {!vehicles.length && (
                  <tr>
                    <td colSpan="4" className={styles.empty}>
                      Add your first vehicle to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2>Expense breakdown</h2>
            <p>All fleet expenses in one ledger.</p>
          </div>

          <div className={styles.breakdown}>
            {(dashboard?.expense_breakdown || []).map((item) => (
              <div
                className={styles.breakdownRow}
                key={item.category}
              >
                <span>{item.category}</span>
                <strong>UGX {money(item.total)}</strong>
              </div>
            ))}

            {!dashboard?.expense_breakdown?.length && (
              <p className={styles.empty}>
                No expenses recorded for this period.
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
