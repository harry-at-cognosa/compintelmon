import { Container } from "react-bootstrap";
import { useAuthStore } from "../stores/useAuthStore";

export default function Dashboard() {
  const { user_name, group_name } = useAuthStore();

  return (
    <Container className="py-4">
      <h3>Dashboard</h3>
      <p className="text-muted">
        Welcome, <strong>{user_name}</strong> ({group_name})
      </p>
      <div className="card">
        <div className="card-body text-muted">
          Dashboard content will be added in future phases.
        </div>
      </div>
    </Container>
  );
}
