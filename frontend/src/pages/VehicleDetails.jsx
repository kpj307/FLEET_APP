import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api";
import AddEntry from "../components/AddEntry";
import VehicleActions from "../components/VehicleActions";
import styles from "../styles/VehicleDetails.module.css";

// ------------------ Utils ------------------
const formatAmount = (num) =>
  Number(num || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const getCalendarPeriod = (period) => {
  const today = new Date();
  let start, end;

  if (period === "weekly") {
    const day = today.getDay(); // Sun = 0
    const diffToMonday = day === 0 ? -6 : 1 - day;

    start = new Date(today);
    start.setDate(today.getDate() + diffToMonday);

    end = new Date(start);
    end.setDate(start.getDate() + 6);

    if (end > today) end = today;
  }

  if (period === "monthly") {
    start = new Date(today.getFullYear(), today.getMonth(), 2);
    end = today;
  }

  if (period === "annually") {
    start = new Date(today.getFullYear(), 0, 2);
    end = today;
  }

  const fmt = (d) => d.toISOString().split("T")[0];
  console.log(`${fmt(start)} -- ${fmt(end)}`)
  return { start: fmt(start), end: fmt(end) };
};

// ------------------ Component ------------------
export default function VehicleDetails() {
  const { id } = useParams();

  const [vehicle, setVehicle] = useState(null);
  const [incomes, setIncomes] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [editing, setEditing] = useState(null);

  const [period, setPeriod] = useState("monthly");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  // ------------------ Period Handling ------------------
  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);

    if (newPeriod === "custom") {
      setStart("");
      setEnd("");
      return;
    }

    const { start, end } = getCalendarPeriod(newPeriod);
    setStart(start);
    setEnd(end);
  };

  // ------------------ API Calls ------------------
  const loadVehicle = async () => {
    try {
      //  Custom without dates → no data
      if (period === "custom" && (!start || !end)) {
        setVehicle((prev) =>
          prev
            ? { ...prev, total_income: 0, total_expense: 0, profit: 0 }
            : prev
        );
        return;
      }

      const params = { start, end };
      const res = await api.get(`/api/vehicles/${id}/`, { params });
      setVehicle(res.data);
    } catch (err) {
      console.error("Failed to load vehicle:", err);
    }
  };

  const loadEntries = async () => {
    if (!id) return;

    //  Custom without dates → no entries
    if (period === "custom" && (!start || !end)) {
      setIncomes([]);
      setExpenses([]);
      return;
    }

    try {
      const params = { vehicle: id, start, end };

      const [incomeRes, expenseRes] = await Promise.all([
        api.get("/api/income/", { params }),
        api.get("/api/expenses/", { params }),
      ]);

      setIncomes(incomeRes.data);
      setExpenses(expenseRes.data);
    } catch (err) {
      console.error("Failed to load entries:", err);
    }
  };

  const reloadAll = () => {
    loadVehicle();
    loadEntries();
  };

  // ------------------ Effects ------------------
  useEffect(() => {
    // Initialize monthly calendar on load
    const { start, end } = getCalendarPeriod("monthly");
    setStart(start);
    setEnd(end);
  }, []);

  useEffect(() => {
    if (id) {
      reloadAll();
      loadVehicle();
      loadEntries();
    }
  }, [id, start, end]);

  // ------------------ delete entry ------------
  const deleteIncome = async (id) => {
    if (!window.confirm("Delete Entry?")) return;
    await api.delete(`/api/income/${id}/`);
    reloadAll();
  };

  const deleteExpense = async (id) => {
    if (!window.confirm("Delete Entry?")) return;
    await api.delete(`/api/expenses/${id}/`);
    reloadAll();
  };

  // ------------------ Totals ------------------
  const totalIncome = incomes.reduce(
    (sum, i) => sum + parseFloat(i.amount),
    0
  );

  const totalExpense = expenses.reduce(
    (sum, e) => sum + parseFloat(e.amount),
    0
  );

  const profit = totalIncome - totalExpense;

  if (!vehicle) return <p>Loading...</p>;

  // Check if custom filter is invalid (no start or end date)
  const isCustomEmpty = period === "custom" && (!start || !end);

  // ------------------ UI ------------------
  return (
    <div className={styles.container}>
      <h2>{vehicle.make}</h2>
      <p>
        <strong>Plate:</strong> {vehicle.plate}
      </p>

      {/* Filters */}
      <div className={styles.filters}>
        <strong>Filter:</strong>
        <div className={styles.buttons}>
          <button
            className={period === "weekly" ? styles.active : ""}
            onClick={() => handlePeriodChange("weekly")}
          >
            Weekly
          </button>

          <button
            className={period === "monthly" ? styles.active : ""}
            onClick={() => handlePeriodChange("monthly")}
          >
            Monthly
          </button>

          <button
            className={period === "annually" ? styles.active : ""}
            onClick={() => handlePeriodChange("annually")}
          >
            Annually
          </button>

          <button
            className={period === "custom" ? styles.active : ""}
            onClick={() => handlePeriodChange("custom")}
          >
            Custom
          </button>
        </div>

        {period === "custom" && (
          <div className={styles.customDates}>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Totals */}
      
        {!isCustomEmpty && (
          <div className={styles.totals}>
            <p>
              <strong>Total Income:</strong> {formatAmount(totalIncome)}
            </p>
            <p>
              <strong>Total Expenses:</strong> {formatAmount(totalExpense)}
            </p>
            <p>
              <strong>Profit:</strong> {formatAmount(profit)}
            </p>
          </div>
        )}

      {/* Add Entries */}
      <div className={styles.addEntries}>
        <h3>Add Income</h3>
        <AddEntry
          vehicleId={vehicle.id}
          type="income"
          onAdded={reloadAll}
        />

        <h3>Add Expense</h3>
        <AddEntry
          vehicleId={vehicle.id}
          type="expense"
          onAdded={reloadAll}
        />
      </div>

      {/* Tables */}
      {!isCustomEmpty && (
        <div className={styles.entries}>
        <h4>Incomes</h4>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Amount</th>
              <th>Description</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {incomes.map((i) => (
              <tr key={i.id}>
                <td>{i.date}</td>
                <td>{formatAmount(i.amount)}</td>
                <td>{i.description || "-"}</td>
                <td className={styles.actions}>
                  <button onClick={() => setEditing({ ...i, __type: "income" })}>✏️</button>
                  <button onClick={() => deleteIncome(i.id)}>🗑️</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <h4>Expenses</h4>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Amount</th>
              <th>Category</th>
              <th>Description</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id}>
                <td>{e.date}</td>
                <td>{formatAmount(e.amount)}</td>
                <td>{e.category || "-"}</td>
                <td>{e.description || "-"}</td>
                <td className={styles.actions}>
                  <button onClick={() => setEditing({ ...e, __type: "expense" })}>✏️</button>
                  <button onClick={() => deleteExpense(e.id)}>🗑️</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {editing && (
          <VehicleActions
            type={editing.__type}
            entry={editing}
            onClose={() => setEditing(null)}
            onSaved={reloadAll}
          />
        )}
      </div>
      )}
    </div>
  );
}
