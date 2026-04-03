import { useEffect, useState } from "react";
import {
  Container, Row, Col, Table, Button, Form, Modal, Badge,
} from "react-bootstrap";
import { PencilSquare, PlusCircle, Files } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";

interface SubjectType {
  subj_type_id: number;
  subj_type_name: string;
  subj_type_desc: string;
  subj_type_enabled: boolean;
}

interface PlaybookTemplate {
  template_id: number;
  subject_type_id: number;
  subject_type: string;
  category_key: string;
  category_name: string;
  category_group: string;
  description: string;
  default_enabled: boolean;
  default_frequency_minutes: number;
  collection_tool: string;
  priority: number;
}

export default function AdminSubjectTypes() {
  const [types, setTypes] = useState<SubjectType[]>([]);
  const [templates, setTemplates] = useState<PlaybookTemplate[]>([]);
  const [selectedType, setSelectedType] = useState<SubjectType | null>(null);
  const [loading, setLoading] = useState(true);

  // Type modal
  const [showTypeModal, setShowTypeModal] = useState(false);
  const [editType, setEditType] = useState<SubjectType | null>(null);
  const [typeName, setTypeName] = useState("");
  const [typeDesc, setTypeDesc] = useState("");
  const [typeEnabled, setTypeEnabled] = useState(true);
  const [savingType, setSavingType] = useState(false);

  // Template modal
  const [showTplModal, setShowTplModal] = useState(false);
  const [editTpl, setEditTpl] = useState<PlaybookTemplate | null>(null);
  const [tplForm, setTplForm] = useState({
    category_key: "", category_name: "", category_group: "web",
    description: "", default_enabled: true, default_frequency_minutes: 360,
    collection_tool: "crawl4ai", priority: 0,
  });
  const [savingTpl, setSavingTpl] = useState(false);

  // Clone modal
  const [showCloneModal, setShowCloneModal] = useState(false);
  const [cloneSource, setCloneSource] = useState<PlaybookTemplate | null>(null);
  const [cloneTargetId, setCloneTargetId] = useState(0);
  const [cloneKey, setCloneKey] = useState("");

  const fetchTypes = () => {
    axiosClient.get("/subject-types").then((r) => { setTypes(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  const fetchTemplates = (typeId: number) => {
    axiosClient.get(`/playbook-templates?subject_type=${types.find(t => t.subj_type_id === typeId)?.subj_type_name || ""}`).then((r) => setTemplates(r.data)).catch(() => {});
  };

  useEffect(() => { fetchTypes(); }, []);

  useEffect(() => {
    if (selectedType) fetchTemplates(selectedType.subj_type_id);
    else setTemplates([]);
  }, [selectedType]);

  // Type CRUD
  const openAddType = () => { setEditType(null); setTypeName(""); setTypeDesc(""); setTypeEnabled(true); setShowTypeModal(true); };
  const openEditType = (t: SubjectType) => { setEditType(t); setTypeName(t.subj_type_name); setTypeDesc(t.subj_type_desc); setTypeEnabled(t.subj_type_enabled); setShowTypeModal(true); };
  const saveType = async () => {
    setSavingType(true);
    try {
      if (editType) {
        await axiosClient.put(`/subject-types/${editType.subj_type_id}`, { subj_type_name: typeName, subj_type_desc: typeDesc, subj_type_enabled: typeEnabled });
      } else {
        await axiosClient.post("/subject-types", { subj_type_name: typeName, subj_type_desc: typeDesc, subj_type_enabled: typeEnabled });
      }
      setShowTypeModal(false);
      fetchTypes();
    } catch {} finally { setSavingType(false); }
  };

  // Template CRUD
  const openAddTpl = () => {
    setEditTpl(null);
    setTplForm({ category_key: "", category_name: "", category_group: "web", description: "", default_enabled: true, default_frequency_minutes: 360, collection_tool: "crawl4ai", priority: 0 });
    setShowTplModal(true);
  };
  const openEditTpl = (t: PlaybookTemplate) => {
    setEditTpl(t);
    setTplForm({ category_key: t.category_key, category_name: t.category_name, category_group: t.category_group, description: t.description, default_enabled: t.default_enabled, default_frequency_minutes: t.default_frequency_minutes, collection_tool: t.collection_tool, priority: t.priority });
    setShowTplModal(true);
  };
  const saveTpl = async () => {
    if (!selectedType) return;
    setSavingTpl(true);
    try {
      if (editTpl) {
        await axiosClient.put(`/playbook-templates/${editTpl.template_id}`, tplForm);
      } else {
        await axiosClient.post("/playbook-templates", { ...tplForm, subject_type_id: selectedType.subj_type_id });
      }
      setShowTplModal(false);
      fetchTemplates(selectedType.subj_type_id);
    } catch {} finally { setSavingTpl(false); }
  };

  // Clone
  const openClone = (t: PlaybookTemplate) => {
    setCloneSource(t);
    setCloneTargetId(types[0]?.subj_type_id || 0);
    setCloneKey(t.category_key);
    setShowCloneModal(true);
  };
  const doClone = async () => {
    if (!cloneSource) return;
    try {
      await axiosClient.post(`/playbook-templates/${cloneSource.template_id}/clone`, { target_subject_type_id: cloneTargetId, new_category_key: cloneKey || null });
      setShowCloneModal(false);
      if (selectedType) fetchTemplates(selectedType.subj_type_id);
    } catch {}
  };

  if (loading) return <Container className="py-4"><p className="text-muted">Loading...</p></Container>;

  return (
    <Container className="py-4">
      <h3>Subject Types & Playbook Templates</h3>
      <p className="text-muted">Manage subject types and their source collection templates.</p>

      <Row>
        <Col md={4}>
          <div className="d-flex justify-content-between align-items-center mb-2">
            <h5 className="mb-0">Subject Types</h5>
            <Button variant="primary" size="sm" onClick={openAddType}><PlusCircle size={12} className="me-1" />Add</Button>
          </div>
          <Table striped bordered hover size="sm">
            <thead><tr><th>Name</th><th>Enabled</th><th style={{ width: 40 }}></th></tr></thead>
            <tbody>
              {types.map((t) => (
                <tr
                  key={t.subj_type_id}
                  onClick={() => setSelectedType(t)}
                  style={{ cursor: "pointer", backgroundColor: selectedType?.subj_type_id === t.subj_type_id ? "#e8f4fd" : undefined }}
                >
                  <td>
                    <strong>{t.subj_type_name}</strong>
                    {t.subj_type_desc && <><br /><small className="text-muted">{t.subj_type_desc}</small></>}
                  </td>
                  <td><Badge bg={t.subj_type_enabled ? "success" : "secondary"}>{t.subj_type_enabled ? "Yes" : "No"}</Badge></td>
                  <td>
                    <Button variant="outline-primary" size="sm" onClick={(e) => { e.stopPropagation(); openEditType(t); }}><PencilSquare size={12} /></Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Col>

        <Col md={8}>
          {selectedType ? (
            <>
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h5 className="mb-0">Templates for "{selectedType.subj_type_name}" ({templates.length})</h5>
                <Button variant="primary" size="sm" onClick={openAddTpl}><PlusCircle size={12} className="me-1" />Add Template</Button>
              </div>
              <Table striped bordered hover size="sm">
                <thead>
                  <tr><th>Key</th><th>Name</th><th>Group</th><th>Tool</th><th>Freq</th><th>On</th><th style={{ width: 70 }}></th></tr>
                </thead>
                <tbody>
                  {templates.map((t) => (
                    <tr key={t.template_id}>
                      <td><code style={{ fontSize: "0.8em" }}>{t.category_key}</code></td>
                      <td>{t.category_name}</td>
                      <td><Badge bg="secondary">{t.category_group}</Badge></td>
                      <td><code>{t.collection_tool}</code></td>
                      <td>{t.default_frequency_minutes}m</td>
                      <td><Badge bg={t.default_enabled ? "success" : "secondary"}>{t.default_enabled ? "Y" : "N"}</Badge></td>
                      <td>
                        <Button variant="outline-primary" size="sm" className="me-1" onClick={() => openEditTpl(t)} title="Edit"><PencilSquare size={12} /></Button>
                        <Button variant="outline-secondary" size="sm" onClick={() => openClone(t)} title="Clone"><Files size={12} /></Button>
                      </td>
                    </tr>
                  ))}
                  {templates.length === 0 && <tr><td colSpan={7} className="text-muted text-center">No templates. Add one or clone from another type.</td></tr>}
                </tbody>
              </Table>
            </>
          ) : (
            <div className="text-center text-muted py-5">Select a subject type to view its templates.</div>
          )}
        </Col>
      </Row>

      {/* Type Modal */}
      <Modal show={showTypeModal} onHide={() => setShowTypeModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>{editType ? "Edit Type" : "Add Type"}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3"><Form.Label>Name</Form.Label><Form.Control value={typeName} onChange={(e) => setTypeName(e.target.value)} disabled={!!editType} /></Form.Group>
          <Form.Group className="mb-3"><Form.Label>Description</Form.Label><Form.Control as="textarea" rows={2} value={typeDesc} onChange={(e) => setTypeDesc(e.target.value)} /></Form.Group>
          <Form.Group><Form.Check type="switch" label="Enabled" checked={typeEnabled} onChange={(e) => setTypeEnabled(e.target.checked)} /></Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowTypeModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={saveType} disabled={savingType || !typeName}>{savingType ? "Saving..." : "Save"}</Button>
        </Modal.Footer>
      </Modal>

      {/* Template Modal */}
      <Modal show={showTplModal} onHide={() => setShowTplModal(false)} centered size="lg">
        <Modal.Header closeButton><Modal.Title>{editTpl ? "Edit Template" : "Add Template"}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Row>
            <Col md={6}>
              <Form.Group className="mb-2"><Form.Label>Category Key</Form.Label><Form.Control value={tplForm.category_key} onChange={(e) => setTplForm({ ...tplForm, category_key: e.target.value })} disabled={!!editTpl} /></Form.Group>
              <Form.Group className="mb-2"><Form.Label>Category Name</Form.Label><Form.Control value={tplForm.category_name} onChange={(e) => setTplForm({ ...tplForm, category_name: e.target.value })} /></Form.Group>
              <Form.Group className="mb-2"><Form.Label>Group</Form.Label>
                <Form.Select value={tplForm.category_group} onChange={(e) => setTplForm({ ...tplForm, category_group: e.target.value })}>
                  {["web", "social", "news", "community", "regulatory", "financial"].map((g) => <option key={g} value={g}>{g}</option>)}
                </Form.Select>
              </Form.Group>
              <Form.Group className="mb-2"><Form.Label>Collection Tool</Form.Label>
                <Form.Select value={tplForm.collection_tool} onChange={(e) => setTplForm({ ...tplForm, collection_tool: e.target.value })}>
                  {["crawl4ai", "feedparser", "httpx", "playwright", "tweepy", "praw"].map((t) => <option key={t} value={t}>{t}</option>)}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group className="mb-2"><Form.Label>Frequency (minutes)</Form.Label><Form.Control type="number" value={tplForm.default_frequency_minutes} onChange={(e) => setTplForm({ ...tplForm, default_frequency_minutes: parseInt(e.target.value) || 360 })} /></Form.Group>
              <Form.Group className="mb-2"><Form.Label>Priority</Form.Label><Form.Control type="number" value={tplForm.priority} onChange={(e) => setTplForm({ ...tplForm, priority: parseInt(e.target.value) || 0 })} /></Form.Group>
              <Form.Group className="mb-2"><Form.Check type="switch" label="Enabled by default" checked={tplForm.default_enabled} onChange={(e) => setTplForm({ ...tplForm, default_enabled: e.target.checked })} /></Form.Group>
              <Form.Group className="mb-2"><Form.Label>Description</Form.Label><Form.Control as="textarea" rows={3} value={tplForm.description} onChange={(e) => setTplForm({ ...tplForm, description: e.target.value })} /></Form.Group>
            </Col>
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowTplModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={saveTpl} disabled={savingTpl || !tplForm.category_key || !tplForm.category_name}>{savingTpl ? "Saving..." : "Save"}</Button>
        </Modal.Footer>
      </Modal>

      {/* Clone Modal */}
      <Modal show={showCloneModal} onHide={() => setShowCloneModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>Clone Template</Modal.Title></Modal.Header>
        <Modal.Body>
          <p>Clone "<strong>{cloneSource?.category_name}</strong>" to another subject type.</p>
          <Form.Group className="mb-3"><Form.Label>Target Subject Type</Form.Label>
            <Form.Select value={cloneTargetId} onChange={(e) => setCloneTargetId(parseInt(e.target.value))}>
              {types.map((t) => <option key={t.subj_type_id} value={t.subj_type_id}>{t.subj_type_name}</option>)}
            </Form.Select>
          </Form.Group>
          <Form.Group className="mb-3"><Form.Label>New Category Key (optional)</Form.Label><Form.Control value={cloneKey} onChange={(e) => setCloneKey(e.target.value)} placeholder="Leave blank to keep same key" /></Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCloneModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={doClone}>Clone</Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}
