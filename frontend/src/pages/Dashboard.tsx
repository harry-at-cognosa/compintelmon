import { useEffect, useState, useRef } from "react";
import { Container, Row, Col, Card, Table, Badge, Button, Spinner } from "react-bootstrap";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";
import { useSettingsStore } from "../stores/useSettingsStore";

interface DashboardStats {
  total_subjects: number;
  total_enabled_sources: number;
  sources_due: number;
  scheduler_running: boolean;
}

interface HealthCheck {
  name: string;
  status: string;
  detail: string;
}

interface RecentRun {
  run_id: number;
  subject_name: string;
  source_name: string;
  status: string;
  started_at: string;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    pending: "secondary",
    ok: "success",
    running: "primary",
    error: "danger",
    no_change: "info",
    skipped: "warning",
  };
  return <Badge bg={colors[status] || "secondary"}>{status}</Badge>;
}

export default function Dashboard() {
  const { user_name, group_name, is_superuser } = useAuthStore();
  const { dashboard_title, dashboard_top, sw_ver, db_ver } = useSettingsStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [runs, setRuns] = useState<RecentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthCheck[]>([]);
  const [toggling, setToggling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = () => {
    Promise.all([
      axiosClient.get("/dashboard/stats"),
      axiosClient.get("/dashboard/recent-runs?limit=10"),
      axiosClient.get("/dashboard/health"),
    ])
      .then(([statsRes, runsRes, healthRes]) => {
        setStats(statsRes.data);
        setRuns(runsRes.data);
        setHealth(healthRes.data.checks || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAll();
  }, []);

  // Auto-refresh when scheduler is running
  useEffect(() => {
    if (stats?.scheduler_running && !pollRef.current) {
      pollRef.current = setInterval(fetchAll, 30000);
    } else if (!stats?.scheduler_running && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [stats?.scheduler_running]);

  const toggleScheduler = async () => {
    if (!stats) return;
    setToggling(true);
    try {
      const endpoint = stats.scheduler_running ? "/scheduler/stop" : "/scheduler/start";
      await axiosClient.post(endpoint);
      fetchAll();
    } catch {
      // handle error
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return (
      <Container className="py-4">
        <p className="text-muted">Loading...</p>
      </Container>
    );
  }

  return (
    <Container className="py-4">
      {/* Dashboard banner */}
      <div className="rounded mb-4 overflow-hidden">
        <div className="bg-tc-400 px-3 py-2">
          <h4 className="mb-0 text-tc-50">{dashboard_title || "Dashboard"}</h4>
        </div>
        <div className="bg-tc-100 px-3 py-2">
          <div>{dashboard_top || `Welcome, ${user_name} (${group_name})`}</div>
          {(sw_ver || db_ver) && (
            <small className="text-muted">{[sw_ver, db_ver].filter(Boolean).join(" · ")}</small>
          )}
        </div>
      </div>

      <Row className="mb-4">
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <Card.Title className="display-6">{stats?.total_subjects ?? 0}</Card.Title>
              <Card.Text className="text-muted">Subjects</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <Card.Title className="display-6">{stats?.total_enabled_sources ?? 0}</Card.Title>
              <Card.Text className="text-muted">Enabled Sources</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <Card.Title
                className="display-6"
                style={{ color: (stats?.sources_due ?? 0) > 0 ? "#dc3545" : undefined }}
              >
                {stats?.sources_due ?? 0}
              </Card.Title>
              <Card.Text className="text-muted">Sources Due</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="text-center">
            <Card.Body>
              <div className="mb-2">
                <Badge
                  bg={stats?.scheduler_running ? "success" : "secondary"}
                  style={{ fontSize: "1.1em" }}
                >
                  {stats?.scheduler_running ? "Running" : "Stopped"}
                </Badge>
              </div>
              <Card.Text className="text-muted mb-2">Scheduler</Card.Text>
              {is_superuser && (
                <Button
                  variant={stats?.scheduler_running ? "outline-danger" : "outline-success"}
                  size="sm"
                  onClick={toggleScheduler}
                  disabled={toggling}
                >
                  {toggling ? (
                    <Spinner animation="border" size="sm" />
                  ) : stats?.scheduler_running ? (
                    "Stop"
                  ) : (
                    "Start"
                  )}
                </Button>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {health.length > 0 && (
        <>
          <h5>System Health</h5>
          <Table size="sm" className="mb-4" style={{ maxWidth: 500 }}>
            <tbody>
              {health.map((h) => (
                <tr key={h.name}>
                  <td style={{ width: 30 }}>
                    {h.status === "ok" ? (
                      <Badge bg="success" style={{ fontSize: "0.7em" }}>OK</Badge>
                    ) : h.status === "warning" ? (
                      <Badge bg="warning" text="dark" style={{ fontSize: "0.7em" }}>WARN</Badge>
                    ) : (
                      <Badge bg="danger" style={{ fontSize: "0.7em" }}>ERR</Badge>
                    )}
                  </td>
                  <td><strong>{h.name}</strong></td>
                  <td><small className="text-muted">{h.detail}</small></td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}

      <h5>Recent Activity</h5>
      {runs.length === 0 ? (
        <p className="text-muted">No collection runs yet.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>Run</th>
              <th>Subject</th>
              <th>Source</th>
              <th>Status</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id}>
                <td>#{r.run_id}</td>
                <td>{r.subject_name}</td>
                <td>{r.source_name}</td>
                <td>{statusBadge(r.status)}</td>
                <td>
                  <small className="text-muted">{formatRelativeTime(r.started_at)}</small>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}
