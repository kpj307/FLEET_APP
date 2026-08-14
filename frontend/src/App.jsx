import { Navigate, Route, Routes } from "react-router-dom";
import useDocumentTitle from "./hooks/useDocumentTitle";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Pricing from "./pages/Pricing";
import PaymentCallback from "./pages/PaymentCallback";
import VehicleList from "./pages/VehicleList";
import VehicleDetails from "./pages/VehicleDetails";
import NotFound from "./pages/NotFound";
import ProtectedRoute from "./components/ProtectedRoute";

function Logout() {
  localStorage.clear();
  return <Navigate to="/login" />;
}

function RegisterAndLogout() {
  localStorage.clear();
  return <Register />;
}

function App() {
  useDocumentTitle();

  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/vehicles"
        element={
          <ProtectedRoute>
            <Layout>
              <VehicleList />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/vehicles/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <VehicleDetails />
            </Layout>
          </ProtectedRoute>
        }
      />

      {/* Backward-compatible route used by the existing VehicleList. */}
      <Route
        path="/api/vehicles/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <VehicleDetails />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/pricing"
        element={
          <ProtectedRoute>
            <Layout>
              <Pricing />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route
          path="/payment/callback"
          element={
              <ProtectedRoute>
                  <Layout>
                      <PaymentCallback />
                  </Layout>
              </ProtectedRoute>
          }
      />

      <Route path="/login" element={<Login />} />
      <Route path="/logout" element={<Logout />} />
      <Route path="/register" element={<RegisterAndLogout />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
