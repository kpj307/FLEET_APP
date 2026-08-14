import styles from "../styles/Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <p>
        © {new Date().getFullYear()} Fleet Tracker • Built for smarter vehicle management
      </p>
    </footer>
  );
}
