import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const TITLE_MAP = {
  "/login": "Login | Fleet Tracker",
  "/register": "Register | Fleet Tracker",
  "/": "Home | Fleet Tracker",
};

export default function useDocumentTitle() {
  const location = useLocation();

  useEffect(() => {
    const path = location.pathname;
    console.log(path)

    if (path.startsWith("/api/vehicles/")) {
        document.title = "Vehicle Details | Fleet Tracker";
    } else {
        document.title = TITLE_MAP[path] || "Fleet Tracker";
    }
  }, [location.pathname]);
}
