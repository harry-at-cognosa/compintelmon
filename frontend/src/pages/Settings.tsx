import { useEffect, useState } from "react";
import { Container, Table } from "react-bootstrap";
import axiosClient from "../api/axiosClient";

interface Setting {
  name: string;
  value: string;
}

export default function Settings() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axiosClient
      .get("/settings")
      .then((res) => setSettings(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <Container className="py-4">
      <h3>Global Settings</h3>
      <p className="text-muted">Superuser only</p>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>Name</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {settings.map((s) => (
              <tr key={s.name}>
                <td>{s.name}</td>
                <td>{s.value}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}
