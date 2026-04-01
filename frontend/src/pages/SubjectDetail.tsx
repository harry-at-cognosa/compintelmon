import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Container, Table, Badge, Form, Button } from "react-bootstrap";
import { ArrowLeft } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";

interface Subject {
  gsubject_id: number;
  gsubject_name: string;
  gsubject_type: string;
  gsubject_status: string;
  enabled: boolean;
}

interface Source {
  source_id: number;
  gsubject_id: number;
  template_id: number | null;
  category_key: string;
  category_name: string;
  enabled: boolean;
  frequency_minutes: number;
  collection_tool: string;
  last_status: string;
  last_collected_at: string | null;
  last_status_text: string;
}

function formatFrequency(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
  if (minutes < 10080) return `${Math.round(minutes / 1440)}d`;
  return `${Math.round(minutes / 10080)}w`;
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    pending: "secondary",
    ok: "success",
    error: "danger",
    rate_limited: "warning",
    auth_required: "info",
  };
  return <Badge bg={colors[status] || "secondary"}>{status}</Badge>;
}

export default function SubjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const auth = useAuthStore();
  const canManage = auth.is_subjectmanager || auth.is_groupadmin || auth.is_superuser;

  useEffect(() => {
    if (!id) return;
    Promise.all([
      axiosClient.get(`/subjects/${id}`),
      axiosClient.get(`/subjects/${id}/sources`),
    ])
      .then(([subjectRes, sourcesRes]) => {
        setSubject(subjectRes.data);
        setSources(sourcesRes.data);
      })
      .catch(() => navigate("/app/subjects"))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const toggleSource = async (source: Source) => {
    if (!canManage) return;
    try {
      const resp = await axiosClient.put(
        `/subjects/${id}/sources/${source.source_id}`,
        { enabled: !source.enabled }
      );
      setSources((prev) =>
        prev.map((s) => (s.source_id === source.source_id ? resp.data : s))
      );
    } catch {
      // handle error
    }
  };

  if (loading) return <Container className="py-4"><p className="text-muted">Loading...</p></Container>;
  if (!subject) return null;

  // Group sources by category_group (derived from template data)
  // Since we don't have category_group on subject_sources, group by collection_tool prefix or just list them
  // For now, show all sources in a single table sorted by source_id

  return (
    <Container className="py-4">
      <Button
        variant="link"
        className="p-0 mb-3 text-decoration-none"
        onClick={() => navigate("/app/subjects")}
      >
        <ArrowLeft className="me-1" /> Back to Subjects
      </Button>

      <div className="d-flex align-items-center mb-3">
        <h3 className="mb-0 me-3">{subject.gsubject_name}</h3>
        <Badge bg="secondary" className="me-2">{subject.gsubject_type}</Badge>
        <Badge bg={subject.enabled ? "success" : "secondary"}>
          {subject.enabled ? "Enabled" : "Disabled"}
        </Badge>
      </div>

      <h5 className="mt-4 mb-3">
        Collection Sources
        <small className="text-muted ms-2">({sources.length})</small>
      </h5>

      {sources.length === 0 ? (
        <p className="text-muted">No sources configured.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>Source</th>
              <th>Tool</th>
              <th style={{ width: 80 }}>Freq</th>
              <th style={{ width: 90 }}>Status</th>
              <th style={{ width: 80 }}>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.source_id}>
                <td>
                  {s.category_name}
                  {s.template_id === null && (
                    <Badge bg="info" className="ms-2" style={{ fontSize: "0.7em" }}>
                      custom
                    </Badge>
                  )}
                </td>
                <td><code>{s.collection_tool}</code></td>
                <td>{formatFrequency(s.frequency_minutes)}</td>
                <td>{statusBadge(s.last_status)}</td>
                <td>
                  <Form.Check
                    type="switch"
                    checked={s.enabled}
                    onChange={() => toggleSource(s)}
                    disabled={!canManage}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}
