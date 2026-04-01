import { Outlet } from "react-router-dom";
import { useAuthStore } from "../stores/useAuthStore";

interface Props {
  requiredRole?: "user" | "subjectmanager" | "groupadmin" | "superuser";
}

function hasRole(
  user: { is_superuser: boolean; is_groupadmin: boolean; is_subjectmanager: boolean },
  role: string
): boolean {
  switch (role) {
    case "superuser":
      return user.is_superuser;
    case "groupadmin":
      return user.is_groupadmin || user.is_superuser;
    case "subjectmanager":
      return user.is_subjectmanager || user.is_groupadmin || user.is_superuser;
    case "user":
    default:
      return true;
  }
}

export default function ProtectedRoute({ requiredRole = "user" }: Props) {
  const auth = useAuthStore();

  if (!auth.isLogged) return null;
  if (!hasRole(auth, requiredRole)) {
    return (
      <div className="container py-4">
        <div className="alert alert-warning">You do not have access to this page.</div>
      </div>
    );
  }

  return <Outlet />;
}
