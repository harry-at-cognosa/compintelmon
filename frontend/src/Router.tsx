import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "./App";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import Settings from "./pages/Settings";
import Logout from "./pages/Logout";
import ProtectedRoute from "./components/ProtectedRoute";

export const Router = createBrowserRouter([
  {
    path: "app",
    element: <App />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "subjects",
        element: <Subjects />,
      },
      {
        path: "logout",
        element: <Logout />,
      },
      {
        path: "su",
        element: <ProtectedRoute requiredRole="superuser" />,
        children: [
          {
            path: "settings",
            element: <Settings />,
          },
        ],
      },
    ],
  },
  {
    path: "login",
    element: <Login />,
  },
  {
    path: "*",
    element: <Navigate to="/login" replace />,
  },
]);
