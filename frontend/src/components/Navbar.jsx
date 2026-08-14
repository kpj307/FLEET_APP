import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import styles from "../styles/Navbar.module.css";

export default function Navbar() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const logout = () => {
    localStorage.clear();
    navigate("/login");
  };

  const closeMenu = () => setOpen(false);

  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>🚛 Fleet Tracker</div>

      <button
        className={styles.menuBtn}
        onClick={() => setOpen(!open)}
      >
        ☰
      </button>

      <div className={`${styles.links} ${open ? styles.show : ""}`}>
        <Link onClick={closeMenu} to="/">
          Dashboard
        </Link>

        <Link onClick={closeMenu} to="/vehicles">
          Vehicles
        </Link>

        <Link onClick={closeMenu} to="/pricing">
          Pricing
        </Link>

        <button
          onClick={logout}
          className={styles.logout}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
