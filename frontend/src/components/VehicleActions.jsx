import { useState } from "react";
import api from "../api";
import styles from "../styles/VehicleActions.module.css";

const expenseCategories = [
  "Routine",
  "Maintenance",
  "Other",
];

const normalizeDate = (dateStr) => {
  // Convert DD-MM-YYYY → YYYY-MM-DD
  if (!dateStr.includes("-")) return dateStr;
  const parts = dateStr.split("-");
  return parts.length === 3
    ? `${parts[2]}-${parts[1]}-${parts[0]}`
    : dateStr;
};

export default function VehicleActions({ type, entry, onClose, onSaved }) {
  const [date, setDate] = useState(normalizeDate(entry.date));
  const [amount, setAmount] = useState(entry.amount);
  const [description, setDescription] = useState(entry.description || "");
  const [category, setCategory] = useState(entry.category || "");

  const endpoint =
    type === "income" ? `/api/income/${entry.id}/`: `/api/expenses/${entry.id}/`;

  const save = async () => {
    if (!date || !amount) {
      alert("Date and amount are required");
      return;
    }

    const payload = {
      date,
      amount,
      description,
    };

    if (type === "expenses") {
      payload.category = category;
    }

    try {
      await api.patch(endpoint, payload);
      onSaved();
      onClose();
    } catch (err) {
      console.error("Failed to save entry:", err);
      alert("Failed to save entry");
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <h3>Edit {type === "income" ? "Income" : "Expense"}</h3>

        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />

        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />

        {type === "expenses" && (
          <input
            type="text"
            placeholder="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        )}

        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <div className={styles.actions}>
          <button onClick={save}>Save</button>
          <button className={styles.cancel} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
