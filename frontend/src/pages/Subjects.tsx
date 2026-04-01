import { useEffect, useState } from "react";
import { Container, Table, Badge } from "react-bootstrap";
import axiosClient from "../api/axiosClient";

interface Subject {
  gsubject_id: number;
  gsubject_name: string;
  gsubject_type: string;
  gsubject_status: string;
  enabled: boolean;
}

export default function Subjects() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axiosClient
      .get("/subjects")
      .then((res) => setSubjects(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <Container className="py-4">
      <h3>Subjects</h3>
      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : subjects.length === 0 ? (
        <p className="text-muted">No subjects configured yet.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {subjects.map((s) => (
              <tr key={s.gsubject_id}>
                <td>{s.gsubject_id}</td>
                <td>{s.gsubject_name}</td>
                <td>{s.gsubject_type}</td>
                <td>{s.gsubject_status}</td>
                <td>
                  <Badge bg={s.enabled ? "success" : "secondary"}>
                    {s.enabled ? "Yes" : "No"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}
