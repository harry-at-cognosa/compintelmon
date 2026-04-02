import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Container, Row, Col, Button, Form, Badge, ListGroup, Spinner,
} from "react-bootstrap";
import { ArrowLeft, SendFill, PlusCircle } from "react-bootstrap-icons";
import Markdown from "react-markdown";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";

interface Conversation {
  conversation_id: number;
  gsubject_id: number;
  conversation_type: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Message {
  message_id: number;
  conversation_id: number;
  role: string;
  content: string;
  message_type: string;
  metadata_json: Record<string, string>;
  status: string;
  created_at: string;
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

export default function SubjectChat() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const auth = useAuthStore();

  const [subjectName, setSubjectName] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [creating, setCreating] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const canManage = auth.is_subjectmanager || auth.is_groupadmin || auth.is_superuser;

  // Fetch subject name
  useEffect(() => {
    if (!id) return;
    axiosClient.get(`/subjects/${id}`).then((res) => setSubjectName(res.data.gsubject_name)).catch(() => {});
  }, [id]);

  // Fetch conversations
  const fetchConversations = useCallback(() => {
    if (!id) return;
    axiosClient.get(`/subjects/${id}/conversations`).then((res) => setConversations(res.data)).catch(() => {});
  }, [id]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Fetch messages for active conversation
  const fetchMessages = useCallback(() => {
    if (!id || !activeConvId) return;
    axiosClient
      .get(`/subjects/${id}/conversations/${activeConvId}/messages`)
      .then((res) => setMessages(res.data))
      .catch(() => {});
  }, [id, activeConvId]);

  useEffect(() => {
    if (activeConvId) {
      fetchMessages();
    } else {
      setMessages([]);
    }
  }, [activeConvId, fetchMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Polling while sending — stop when assistant responds
  useEffect(() => {
    if (sending && !pollRef.current) {
      pollRef.current = setInterval(fetchMessages, 2000);
    }
    // Check if assistant has responded (non-pending)
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    if (lastAssistant && lastAssistant.status !== "pending" && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
      setSending(false);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [messages, fetchMessages]);

  const createConversation = async (mode: "update" | "query") => {
    if (!id) return;
    setCreating(true);
    try {
      const title = mode === "update" ? "Data Update" : "Query";
      const resp = await axiosClient.post(`/subjects/${id}/conversations`, {
        conversation_type: mode,
        title,
      });
      setActiveConvId(resp.data.conversation_id);
      fetchConversations();
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeConvId || !id) return;
    setSending(true);
    const content = input.trim();
    setInput("");

    // Optimistic: add user message immediately
    const tempMsg: Message = {
      message_id: Date.now(),
      conversation_id: activeConvId,
      role: "user",
      content,
      message_type: "text",
      metadata_json: {},
      status: "ok",
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempMsg]);

    try {
      await axiosClient.post(`/subjects/${id}/conversations/${activeConvId}/messages`, { content });
      // Fetch immediately to get the user message + pending assistant message from DB
      setTimeout(fetchMessages, 500);
    } catch {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const activeConv = conversations.find((c) => c.conversation_id === activeConvId);

  return (
    <Container fluid className="py-3" style={{ maxWidth: 1200 }}>
      <Button
        variant="link"
        className="p-0 mb-3 text-decoration-none"
        onClick={() => navigate(`/app/subjects/${id}`)}
      >
        <ArrowLeft className="me-1" /> Back to {subjectName || "Subject"}
      </Button>

      <h4>
        Chat — {subjectName}
        {activeConv && (
          <Badge
            bg={activeConv.conversation_type === "update" ? "warning" : "info"}
            className="ms-2"
            style={{ fontSize: "0.6em" }}
          >
            {activeConv.conversation_type}
          </Badge>
        )}
      </h4>

      <Row>
        {/* Conversation sidebar */}
        <Col md={3}>
          <div className="d-flex gap-1 mb-2">
            <Button
              variant="outline-warning"
              size="sm"
              className="flex-fill"
              onClick={() => createConversation("update")}
              disabled={creating || !canManage}
              title="New conversation to provide data updates"
            >
              <PlusCircle size={12} className="me-1" />
              Update
            </Button>
            <Button
              variant="outline-info"
              size="sm"
              className="flex-fill"
              onClick={() => createConversation("query")}
              disabled={creating || !canManage}
              title="New conversation to ask questions"
            >
              <PlusCircle size={12} className="me-1" />
              Query
            </Button>
          </div>
          <ListGroup>
            {conversations.map((c) => (
              <ListGroup.Item
                key={c.conversation_id}
                active={c.conversation_id === activeConvId}
                onClick={() => setActiveConvId(c.conversation_id)}
                style={{ cursor: "pointer" }}
                className="py-2"
              >
                <div className="d-flex justify-content-between align-items-center">
                  <small className="fw-bold">{c.title || `#${c.conversation_id}`}</small>
                  <Badge bg={c.conversation_type === "update" ? "warning" : "info"} style={{ fontSize: "0.7em" }}>
                    {c.conversation_type}
                  </Badge>
                </div>
                <small className="text-muted">{formatRelativeTime(c.updated_at)}</small>
              </ListGroup.Item>
            ))}
            {conversations.length === 0 && (
              <ListGroup.Item className="text-muted text-center py-3">
                <small>No conversations yet</small>
              </ListGroup.Item>
            )}
          </ListGroup>
        </Col>

        {/* Chat area */}
        <Col md={9}>
          {!activeConvId ? (
            <div className="text-center text-muted py-5">
              <p>Select a conversation or create a new one.</p>
              <p>
                <strong>Update</strong> — provide new data (saved for future analyses)<br />
                <strong>Query</strong> — ask questions about collected data
              </p>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div
                className="border rounded p-3 mb-3"
                style={{ height: "55vh", overflowY: "auto", backgroundColor: "#fafafa" }}
              >
                {messages.length === 0 && (
                  <p className="text-muted text-center mt-4">
                    {activeConv?.conversation_type === "update"
                      ? 'Provide information or URLs to add to this subject\'s intelligence.'
                      : 'Ask a question about the collected data.'}
                  </p>
                )}
                {messages.map((m) => (
                  <div
                    key={m.message_id}
                    className={`mb-3 d-flex ${m.role === "user" ? "justify-content-end" : "justify-content-start"}`}
                  >
                    <div
                      className={`p-2 rounded ${
                        m.role === "user"
                          ? "bg-primary text-white"
                          : m.status === "pending"
                          ? "bg-light border"
                          : m.status === "error"
                          ? "bg-danger bg-opacity-10 border border-danger"
                          : "bg-white border"
                      }`}
                      style={{ maxWidth: "80%", fontSize: "0.9em" }}
                    >
                      {m.role === "assistant" && m.status === "pending" ? (
                        <div className="d-flex align-items-center text-muted">
                          <Spinner animation="border" size="sm" className="me-2" />
                          Thinking...
                        </div>
                      ) : m.role === "assistant" ? (
                        <>
                          {m.message_type === "data_saved" && (
                            <Badge bg="success" className="mb-1">Data Saved</Badge>
                          )}
                          <Markdown>{m.content}</Markdown>
                        </>
                      ) : (
                        <span style={{ whiteSpace: "pre-wrap" }}>{m.content}</span>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <Form
                className="d-flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  sendMessage();
                }}
              >
                <Form.Control
                  as="textarea"
                  rows={2}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    activeConv?.conversation_type === "update"
                      ? "Provide data or URLs..."
                      : "Ask a question..."
                  }
                  disabled={sending}
                  style={{ resize: "none" }}
                />
                <Button
                  type="submit"
                  variant="primary"
                  disabled={sending || !input.trim()}
                  style={{ minWidth: 50 }}
                >
                  {sending ? <Spinner size="sm" /> : <SendFill />}
                </Button>
              </Form>
            </>
          )}
        </Col>
      </Row>
    </Container>
  );
}
