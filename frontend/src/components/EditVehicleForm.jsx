import { useState } from "react";
import api from "../api";
import styles from "../styles/EditVehicleForm.module.css";

export default function EditVehicleForm({ vehicle, onClose, onSaved }) {
  const [make, setMake] = useState(vehicle.make);
  const [plate, setPlate] = useState(vehicle.plate);

  const save = async () => {
    await api.patch(`/api/vehicles/${vehicle.id}/`, {
      make,
      plate: plate,
    });
    onSaved();
    onClose();
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <h3>Edit Vehicle</h3>

        <input
          type="text"
          value={make}
          onChange={e => setMake(e.target.value)}
        />
        <input
          type="text"
          value={plate}
          onChange={e => setPlate(e.target.value)}
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
