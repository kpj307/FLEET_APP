import { useState } from "react";
import api from "../api";
import styles from "../styles/AddEntry.module.css";

const expenseCategories = [
  "Routine",
  "Maintenance",
  "Other",
];

export default function AddEntry({ vehicleId, type, onAdded }) {
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [date, setDate] = useState("");
  const [description, setDescription] = useState("")

  const submit = async () => {
    if (!amount) return;

    const today = new Date().toISOString().split("T")[0];

    const payload = {
      vehicle: vehicleId,
      amount,
      description,
      date: date || today,
    };

    if (type === "expense") {
      payload.category = category || "General";
    }

    await api.post(type === "income" ? "/api/income/" : "/api/expenses/", payload);

    setAmount("");
    setDate("");
    setCategory("");
    setDescription("");
    onAdded();
  };

  return (
    <div className={styles.form}>
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
      <input
        type="number"
        placeholder="Amount"
        value={amount}
        onChange={e => setAmount(e.target.value)}
      />

      <input
        type="text"
        placeholder="Description"
        value={description}
        onChange={e => setDescription(e.target.value)}
      />
  
      {type === "expense" && (
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          required
        >
          <option value="">Select Category</option>
          {expenseCategories.map((cat) => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      )}

      <button onClick={submit}>Add {type}</button>
    </div>
  );
}
