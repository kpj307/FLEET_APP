import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import AddVehicleForm from "../components/AddVehicleForm";
import EditVehicleForm from "../components/EditVehicleForm";
import styles from "../styles/VehicleList.module.css";

export default function VehicleList() {
  const [vehicles, setVehicles] = useState([]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const navigate = useNavigate();

  const loadVehicles = async () => {
    const res = await api.get("/api/vehicles/");
    setVehicles(res.data);
  };

  useEffect(() => {
    loadVehicles();
  }, []);

  const deleteVehicle = async (id) => {
    if (!window.confirm("Delete vehicle?")) return;
    await api.delete(`/api/vehicles/${id}/`);
    loadVehicles();
  };

  const filtered = vehicles.filter(v =>
    v.make.toLowerCase().includes(search.toLowerCase()) ||
    v.plate.toLowerCase().includes(search.toLowerCase())
  );

  return (
      <div className={styles.container}>
        <AddVehicleForm onAdded={loadVehicles} />

        <input
          className={styles.search}
          placeholder="Search vehicles..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />

          <table className={styles.table}>
            <thead>
              <tr>
                <th>Vehicle</th>
                <th>Income</th>
                <th>Expenses</th>
                <th>Profit</th>
                <th>Actions</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(v => (
                <tr key={v.id}>
                  <td onClick={() => navigate(`/api/vehicles/${v.id}/`)}>{v.plate}</td>
                  <td>{parseFloat(v.total_income).toLocaleString()}</td>
                  <td>{parseFloat(v.total_expense).toLocaleString()}</td>
                  <td className={v.profit >= 0 ? styles.profit : styles.loss}>
                    {parseFloat(v.profit).toLocaleString()}
                  </td>
                  <td className={styles.actions}>
                    <button onClick={() => setEditing(v)}>✏️</button>
                    <button onClick={() => deleteVehicle(v.id)}>🗑️</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
    
        {editing && (
          <EditVehicleForm
            vehicle={editing}
            onClose={() => setEditing(null)}
            onSaved={loadVehicles}
          />
        )}
    </div>
  );
}
