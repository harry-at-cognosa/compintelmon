import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Container, Table, Badge, Form, Button, Spinner, Collapse, Card } from "react-bootstrap";
import { ArrowLeft, PlayCircle, CollectionPlay, Search, CheckCircleFill, BarChart, FileText, ChatDots } from "react-bootstrap-icons";
import Markdown from "react-markdown";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";

interface Subject {
  gsubject_id: number;
  gsubject_name: string;
  gsubject_type: string;
  gsubject_status: string;
  gsubject_status_text: string;
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
  user_inputs: Record<string, string>;
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

interface Analysis {
  analysis_id: number;
  gsubject_id: number;
  created_at: string;
  analysis_type: string;
  summary: string;
  key_findings: { category: string; finding: string; severity: string; source_key: string }[];
  signals: { signal_type: string; description: string; confidence: string; source_key: string }[];
  sources_analyzed: string[];
  status: string;
  error_detail: string | null;
}

interface Report {
  report_id: number;
  analysis_id: number;
  gsubject_id: number;
  created_at: string;
  report_type: string;
  title: string;
  content_markdown: string;
  status: string;
  error_detail: string | null;
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
  const [discovering, setDiscovering] = useState(false);
  const discoverPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [collectingSources, setCollectingSources] = useState<Set<number>>(new Set());
  const [expandedSource, setExpandedSource] = useState<number | null>(null);
  const [runs, setRuns] = useState<SourceRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [expandedAnalysis, setExpandedAnalysis] = useState<number | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [expandedReport, setExpandedReport] = useState<number | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const analyzePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
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
      axiosClient.get(`/subjects/${id}/analyses?limit=5`),
      axiosClient.get(`/subjects/${id}/reports?limit=5`),
    ])
      .then(([subjectRes, sourcesRes, analysesRes, reportsRes]) => {
        setSubject(subjectRes.data);
        setSources(sourcesRes.data);
        setAnalyses(analysesRes.data);
        setReports(reportsRes.data);
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
      const enabledIds = new Set(sources.filter((s) => s.enabled).map((s) => s.source_id));
      setCollectingSources(enabledIds);
      setTimeout(fetchSources, 1000);
    } catch {
      // handle error
    } finally {
      setCollecting(false);
    }
  };

  const discoverSources = async () => {
    setDiscovering(true);
    try {
      await axiosClient.post(`/subjects/${id}/discover`);
      // Also refetch subject to see status updates
      const refetchSubject = () => {
        axiosClient.get(`/subjects/${id}`).then((res) => setSubject(res.data)).catch(() => {});
        fetchSources();
      };
      // Poll every 5s for up to 90s
      discoverPollRef.current = setInterval(refetchSubject, 5000);
      setTimeout(() => {
        if (discoverPollRef.current) {
          clearInterval(discoverPollRef.current);
          discoverPollRef.current = null;
        }
        setDiscovering(false);
        refetchSubject();
      }, 90000);
    } catch {
      setDiscovering(false);
    }
  };

  const fetchAnalysesAndReports = () => {
    if (!id) return;
    axiosClient.get(`/subjects/${id}/analyses?limit=5`).then((res) => setAnalyses(res.data)).catch(() => {});
    axiosClient.get(`/subjects/${id}/reports?limit=5`).then((res) => setReports(res.data)).catch(() => {});
  };

  const analyzeSubject = async () => {
    setAnalyzing(true);
    try {
      await axiosClient.post(`/subjects/${id}/analyze`);
      // Poll for completion
      analyzePollRef.current = setInterval(fetchAnalysesAndReports, 5000);
      setTimeout(() => {
        if (analyzePollRef.current) {
          clearInterval(analyzePollRef.current);
          analyzePollRef.current = null;
        }
        setAnalyzing(false);
        fetchAnalysesAndReports();
      }, 120000);
    } catch {
      setAnalyzing(false);
    }
  };

  // Stop analyzing spinner when analysis completes
  useEffect(() => {
    if (analyzing && analyses.length > 0 && analyses[0].status !== "pending" && analyses[0].status !== "running") {
      setAnalyzing(false);
      if (analyzePollRef.current) {
        clearInterval(analyzePollRef.current);
        analyzePollRef.current = null;
      }
    }
  }, [analyses, analyzing]);

  const generateReport = async (analysisId: number, reportType: string = "battlecard") => {
    setGeneratingReport(true);
    try {
      await axiosClient.post(`/subjects/${id}/analyses/${analysisId}/report`, { report_type: reportType });
      // Poll for completion
      const pollId = setInterval(fetchAnalysesAndReports, 5000);
      setTimeout(() => {
        clearInterval(pollId);
        setGeneratingReport(false);
        fetchAnalysesAndReports();
      }, 90000);
    } catch {
      setGeneratingReport(false);
    }
  };

  // Stop generating spinner when report completes
  useEffect(() => {
    if (generatingReport && reports.length > 0 && reports[0].status !== "pending" && reports[0].status !== "running") {
      setGeneratingReport(false);
    }
  }, [reports, generatingReport]);

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
      {subject.gsubject_status_text && (
        <p className="text-muted mb-0">
          <small>{subject.gsubject_status_text}</small>
        </p>
      )}

      <div className="d-flex align-items-center mt-4 mb-3">
        <h5 className="mb-0">
          Collection Sources
          <small className="text-muted ms-2">({sources.length})</small>
        </h5>
        {canManage && (
          <>
            <Button
              variant="outline-primary"
              size="sm"
              className="ms-3"
              onClick={discoverSources}
              disabled={discovering}
              title="Run Signal Agent to discover source URLs from the subject name"
            >
              {discovering ? (
                <Spinner animation="border" size="sm" className="me-1" />
              ) : (
                <Search className="me-1" />
              )}
              Discover
            </Button>
            <Button
              variant="primary"
              size="sm"
              className="ms-2"
              onClick={collectAll}
              disabled={collecting || sources.every((s) => !s.enabled)}
              title="Collect data from all enabled sources"
            >
              {collecting ? (
                <Spinner animation="border" size="sm" className="me-1" />
              ) : (
                <CollectionPlay className="me-1" />
              )}
              Collect All
            </Button>
            <Button
              variant="outline-info"
              size="sm"
              className="ms-2"
              onClick={analyzeSubject}
              disabled={analyzing}
              title="Run Fusion Agent to extract competitive intelligence from collected data"
            >
              {analyzing ? (
                <Spinner animation="border" size="sm" className="me-1" />
              ) : (
                <BarChart className="me-1" />
              )}
              Analyze
            </Button>
            <Button
              variant="outline-secondary"
              size="sm"
              className="ms-2"
              onClick={() => navigate(`/app/subjects/${id}/chat`)}
              title="Open chat to provide updates or ask questions"
            >
              <ChatDots className="me-1" />
              Chat
            </Button>
          </>
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
                    {Object.values(s.user_inputs || {}).some((v) => v) ? (
                      <CheckCircleFill className="ms-2 text-success" size={12} title="URLs configured" />
                    ) : (
                      <small className="ms-2 text-warning" title="No URLs configured yet">needs config</small>
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

      {/* ── Analyses Section ── */}
      <h5 className="mt-5 mb-3">
        <BarChart className="me-2" />
        Analyses
        <small className="text-muted ms-2">({analyses.length})</small>
      </h5>

      {analyses.length === 0 ? (
        <p className="text-muted">No analyses yet. Click "Analyze" to extract intelligence from collected data.</p>
      ) : (
        <div>
          {analyses.map((a) => (
            <Card key={a.analysis_id} className="mb-2">
              <Card.Body
                style={{ cursor: "pointer" }}
                onClick={() => setExpandedAnalysis(expandedAnalysis === a.analysis_id ? null : a.analysis_id)}
              >
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <strong>Analysis #{a.analysis_id}</strong>
                    <span className="ms-2">{statusBadge(a.status)}</span>
                    <small className="ms-2 text-muted">{formatRelativeTime(a.created_at)}</small>
                  </div>
                  {canManage && a.status === "ok" && (
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        generateReport(a.analysis_id);
                      }}
                      disabled={generatingReport}
                      title="Run Quill Agent to generate a battlecard report"
                    >
                      {generatingReport ? <Spinner size="sm" /> : <><FileText size={14} className="me-1" />Generate Report</>}
                    </Button>
                  )}
                </div>
                {a.summary && <p className="mt-2 mb-0 text-muted" style={{ fontSize: "0.9em" }}>{a.summary.substring(0, 200)}...</p>}
              </Card.Body>
              <Collapse in={expandedAnalysis === a.analysis_id}>
                <div className="px-3 pb-3">
                  {a.summary && (
                    <div className="mb-3">
                      <strong>Summary:</strong>
                      <p style={{ whiteSpace: "pre-wrap" }}>{a.summary}</p>
                    </div>
                  )}
                  {a.key_findings && a.key_findings.length > 0 && (
                    <div className="mb-3">
                      <strong>Key Findings ({a.key_findings.length}):</strong>
                      <Table size="sm" className="mt-1">
                        <thead><tr><th>Severity</th><th>Finding</th><th>Source</th></tr></thead>
                        <tbody>
                          {a.key_findings.map((f, i) => (
                            <tr key={i}>
                              <td><Badge bg={f.severity === "high" ? "danger" : f.severity === "medium" ? "warning" : "secondary"}>{f.severity}</Badge></td>
                              <td>{f.finding}</td>
                              <td><small>{f.source_key}</small></td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  )}
                  {a.signals && a.signals.length > 0 && (
                    <div>
                      <strong>Signals ({a.signals.length}):</strong>
                      <Table size="sm" className="mt-1">
                        <thead><tr><th>Confidence</th><th>Type</th><th>Description</th></tr></thead>
                        <tbody>
                          {a.signals.map((s, i) => (
                            <tr key={i}>
                              <td><Badge bg={s.confidence === "high" ? "success" : s.confidence === "medium" ? "info" : "secondary"}>{s.confidence}</Badge></td>
                              <td><code>{s.signal_type}</code></td>
                              <td>{s.description}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  )}
                  {a.error_detail && <p className="text-danger">{a.error_detail}</p>}
                </div>
              </Collapse>
            </Card>
          ))}
        </div>
      )}

      {/* ── Reports Section ── */}
      <h5 className="mt-5 mb-3">
        <FileText className="me-2" />
        Reports
        <small className="text-muted ms-2">({reports.length})</small>
      </h5>

      {reports.length === 0 ? (
        <p className="text-muted">No reports yet. Generate a report from an analysis above.</p>
      ) : (
        <div>
          {reports.map((r) => (
            <Card key={r.report_id} className="mb-2">
              <Card.Body
                style={{ cursor: "pointer" }}
                onClick={() => setExpandedReport(expandedReport === r.report_id ? null : r.report_id)}
              >
                <div className="d-flex justify-content-between">
                  <div>
                    <strong>{r.title || `Report #${r.report_id}`}</strong>
                    <Badge bg="secondary" className="ms-2">{r.report_type}</Badge>
                    <span className="ms-2">{statusBadge(r.status)}</span>
                    <small className="ms-2 text-muted">{formatRelativeTime(r.created_at)}</small>
                  </div>
                </div>
              </Card.Body>
              <Collapse in={expandedReport === r.report_id}>
                <div className="px-3 pb-3">
                  {r.status === "ok" && r.content_markdown ? (
                    <div className="border rounded p-3 bg-white">
                      <Markdown>{r.content_markdown}</Markdown>
                    </div>
                  ) : r.error_detail ? (
                    <p className="text-danger">{r.error_detail}</p>
                  ) : (
                    <p className="text-muted">Report is {r.status}...</p>
                  )}
                </div>
              </Collapse>
            </Card>
          ))}
        </div>
      )}
    </Container>
  );
}
