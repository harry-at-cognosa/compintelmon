import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Container, Table, Badge, Form, Button, Spinner, Collapse } from "react-bootstrap";
import { ArrowLeft, PlayCircle, CollectionPlay } from "react-bootstrap-icons";
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

interface SourceRun {
  run_id: number;
  source_id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  items_collected: number;
  error_detail: string | null;
  data_hash: string | null;
}

function formatFrequency(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
  if (minutes < 10080) return `${Math.round(minutes / 1440)}d`;
  return `${Math.round(minutes / 10080)}w`;
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    pending: "secondary",
    ok: "success",
    running: "primary",
    error: "danger",
    no_change: "info",
    skipped: "warning",
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
  const [collecting, setCollecting] = useState(false);
  const [collectingSources, setCollectingSources] = useState<Set<number>>(new Set());
  const [expandedSource, setExpandedSource] = useState<number | null>(null);
  const [runs, setRuns] = useState<SourceRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const auth = useAuthStore();
  const canManage = auth.is_subjectmanager || auth.is_groupadmin || auth.is_superuser;

  const fetchSources = useCallback(() => {
    if (!id) return;
    axiosClient.get(`/subjects/${id}/sources`).then((res) => setSources(res.data)).catch(() => {});
  }, [id]);

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

  // Polling: refresh sources while any are running
  useEffect(() => {
    const hasRunning = sources.some(
      (s) => s.last_status === "running" || collectingSources.size > 0
    );
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(fetchSources, 3000);
    } else if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
      setCollectingSources(new Set());
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sources, collectingSources, fetchSources]);

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

  const collectSource = async (source: Source) => {
    try {
      setCollectingSources((prev) => new Set(prev).add(source.source_id));
      await axiosClient.post(`/subjects/${id}/sources/${source.source_id}/collect`);
      // Start polling
      setTimeout(fetchSources, 1000);
    } catch {
      setCollectingSources((prev) => {
        const next = new Set(prev);
        next.delete(source.source_id);
        return next;
      });
    }
  };

  const collectAll = async () => {
    setCollecting(true);
    try {
      await axiosClient.post(`/subjects/${id}/collect-all`);
      // Mark all enabled as collecting
      const enabledIds = new Set(sources.filter((s) => s.enabled).map((s) => s.source_id));
      setCollectingSources(enabledIds);
      setTimeout(fetchSources, 1000);
    } catch {
      // handle error
    } finally {
      setCollecting(false);
    }
  };

  const toggleRuns = async (sourceId: number) => {
    if (expandedSource === sourceId) {
      setExpandedSource(null);
      return;
    }
    setExpandedSource(sourceId);
    setRunsLoading(true);
    try {
      const resp = await axiosClient.get(`/subjects/${id}/sources/${sourceId}/runs?limit=5`);
      setRuns(resp.data);
    } catch {
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  };

  if (loading)
    return (
      <Container className="py-4">
        <p className="text-muted">Loading...</p>
      </Container>
    );
  if (!subject) return null;

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
        <Badge bg="secondary" className="me-2">
          {subject.gsubject_type}
        </Badge>
        <Badge bg={subject.enabled ? "success" : "secondary"}>
          {subject.enabled ? "Enabled" : "Disabled"}
        </Badge>
      </div>

      <div className="d-flex align-items-center mt-4 mb-3">
        <h5 className="mb-0">
          Collection Sources
          <small className="text-muted ms-2">({sources.length})</small>
        </h5>
        {canManage && (
          <Button
            variant="primary"
            size="sm"
            className="ms-3"
            onClick={collectAll}
            disabled={collecting || sources.every((s) => !s.enabled)}
          >
            {collecting ? (
              <Spinner animation="border" size="sm" className="me-1" />
            ) : (
              <CollectionPlay className="me-1" />
            )}
            Collect All
          </Button>
        )}
      </div>

      {sources.length === 0 ? (
        <p className="text-muted">No sources configured.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>Source</th>
              <th>Tool</th>
              <th style={{ width: 70 }}>Freq</th>
              <th style={{ width: 90 }}>Status</th>
              <th style={{ width: 100 }}>Last Run</th>
              <th style={{ width: 75 }}>Enabled</th>
              {canManage && <th style={{ width: 50 }}>Run</th>}
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <>
                <tr
                  key={s.source_id}
                  onClick={() => toggleRuns(s.source_id)}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    {s.category_name}
                    {s.template_id === null && (
                      <Badge bg="info" className="ms-2" style={{ fontSize: "0.7em" }}>
                        custom
                      </Badge>
                    )}
                  </td>
                  <td>
                    <code>{s.collection_tool}</code>
                  </td>
                  <td>{formatFrequency(s.frequency_minutes)}</td>
                  <td>{statusBadge(s.last_status)}</td>
                  <td>
                    <small className="text-muted">
                      {formatRelativeTime(s.last_collected_at)}
                    </small>
                  </td>
                  <td>
                    <Form.Check
                      type="switch"
                      checked={s.enabled}
                      onChange={(e) => {
                        e.stopPropagation();
                        toggleSource(s);
                      }}
                      disabled={!canManage}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </td>
                  {canManage && (
                    <td>
                      <Button
                        variant="outline-success"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          collectSource(s);
                        }}
                        disabled={!s.enabled || collectingSources.has(s.source_id)}
                        title="Collect now"
                      >
                        {collectingSources.has(s.source_id) ? (
                          <Spinner animation="border" size="sm" />
                        ) : (
                          <PlayCircle size={14} />
                        )}
                      </Button>
                    </td>
                  )}
                </tr>
                {/* Expandable run history */}
                <tr key={`runs-${s.source_id}`} style={{ display: expandedSource === s.source_id ? undefined : "none" }}>
                  <td colSpan={canManage ? 7 : 6} className="bg-light p-0">
                    <Collapse in={expandedSource === s.source_id}>
                      <div className="p-2">
                        {runsLoading ? (
                          <small className="text-muted">Loading runs...</small>
                        ) : runs.length === 0 ? (
                          <small className="text-muted">No runs yet</small>
                        ) : (
                          <Table size="sm" className="mb-0" borderless>
                            <thead>
                              <tr>
                                <th><small>Run</small></th>
                                <th><small>Started</small></th>
                                <th><small>Status</small></th>
                                <th><small>Items</small></th>
                                <th><small>Error</small></th>
                              </tr>
                            </thead>
                            <tbody>
                              {runs.map((r) => (
                                <tr key={r.run_id}>
                                  <td><small>#{r.run_id}</small></td>
                                  <td><small>{formatRelativeTime(r.started_at)}</small></td>
                                  <td>{statusBadge(r.status)}</td>
                                  <td><small>{r.items_collected}</small></td>
                                  <td>
                                    <small className="text-danger">
                                      {r.error_detail ? r.error_detail.substring(0, 80) : ""}
                                    </small>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </Table>
                        )}
                      </div>
                    </Collapse>
                  </td>
                </tr>
              </>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}
