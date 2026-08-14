import { useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import { ACCESS_TOKEN, REFRESH_TOKEN } from "../constants";
import "../styles/Form.css";
import LoadingIndicator from "./LoadingIndicator";

function Form({ route, method }) {
  const [username, setUsername] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const name = method === "login" ? "Login" : "Create Fleet";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (method === "register") {
        await api.post(route, {
          username,
          password,
          business_name: businessName,
        });

        const loginResponse = await api.post("/api/token/", {
          username,
          password,
        });

        localStorage.setItem(
          ACCESS_TOKEN,
          loginResponse.data.access
        );
        localStorage.setItem(
          REFRESH_TOKEN,
          loginResponse.data.refresh
        );

        navigate("/");
        return;
      }

      const response = await api.post(route, {
        username,
        password,
      });

      localStorage.setItem(
        ACCESS_TOKEN,
        response.data.access
      );
      localStorage.setItem(
        REFRESH_TOKEN,
        response.data.refresh
      );

      navigate("/");
    } catch (err) {
      const data = err.response?.data;

      setError(
        data?.username?.[0] ||
          data?.business_name?.[0] ||
          data?.password?.[0] ||
          data?.detail ||
          "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="form-container">
      <h1>{name}</h1>

      {method === "register" && (
        <>
          <p>Create your owner account and fleet workspace.</p>

          <input
            className="form-input"
            type="text"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            placeholder="Fleet / Business Name"
            required
          />
        </>
      )}

      <input
        className="form-input"
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
        required
      />

      <input
        className="form-input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        minLength={8}
        required
      />

      {error && <p className="form-error">{error}</p>}

      {loading && <LoadingIndicator />}

      <button
        className="form-button"
        type="submit"
        disabled={loading}
      >
        {loading ? "Please wait..." : name}
      </button>

      {method === "login" && (
        <p className="form-footer">
          Don’t have an account?{" "}
          <span
            className="form-link"
            onClick={() => navigate("/register")}
          >
            Register
          </span>
        </p>
      )}

      {method === "register" && (
        <p className="form-footer">
          Already have an account?{" "}
          <span
            className="form-link"
            onClick={() => navigate("/login")}
          >
            Login
          </span>
        </p>
      )}
    </form>
  );
}

export default Form;
