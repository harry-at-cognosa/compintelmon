import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "./App";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import SubjectDetail from "./pages/SubjectDetail";
import Settings from "./pages/Settings";
import GroupSettings from "./pages/GroupSettings";
import SubjectChat from "./pages/SubjectChat";
import AdminSubjectTypes from "./pages/AdminSubjectTypes";
import ManageGroups from "./pages/ManageGroups";
import ManageUsers from "./pages/ManageUsers";
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
        path: "subjects/:id",
        element: <SubjectDetail />,
      },
      {
        path: "subjects/:id/chat",
        element: <SubjectChat />,
      },
      {
        path: "logout",
        element: <Logout />,
      },
      {
        path: "admin",
        element: <ProtectedRoute requiredRole="groupadmin" />,
        children: [
          {
            path: "group-settings",
            element: <GroupSettings />,
          },
          {
            path: "users",
            element: <ManageUsers />,
          },
        ],
      },
      {
        path: "su",
        element: <ProtectedRoute requiredRole="superuser" />,
        children: [
          {
            path: "settings",
            element: <Settings />,
          },
          {
            path: "subject-types",
            element: <AdminSubjectTypes />,
          },
          {
            path: "groups",
            element: <ManageGroups />,
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
