import Navbar from "./Navbar";
import Footer from "./Footer";
import styles from "../styles/Layout.module.css";

export default function Layout({ children }) {
  return (
    <div className={styles.page}>
      <Navbar />
      <main className={styles.content}>{children}</main>
      <Footer />
    </div>
  );
}
