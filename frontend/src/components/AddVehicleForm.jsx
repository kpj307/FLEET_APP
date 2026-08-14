import { useState } from "react";
import api from "../api";
import styles from "../styles/AddVehicleForm.module.css";

export default function AddVehicleForm({ onAdded }) {
  const [make, setMake] = useState("");
  const [plate, setPlate] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!make || !plate) return;

    try {
      setLoading(true);
      await api.post("/api/vehicles/", {
        make,
        plate: plate,
      });

      setMake("");
      setPlate("");
      onAdded();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.card}>
      <h3>Add Vehicle</h3>

      <div className={styles.form}>
        <input
          type="text"
          placeholder="Vehicle make"
          value={make}
          onChange={e => setMake(e.target.value)}
        />
        <input
          type="text"
          placeholder="Plate number"
          value={plate}
          onChange={e => setPlate(e.target.value)}
        />
        <button onClick={submit} disabled={loading}>
          {loading ? "Adding..." : "Add Vehicle"}
        </button>
      </div>
    </div>
  );
}
