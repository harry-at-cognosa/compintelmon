import { useEffect, useState } from "react";
import { Container, Table, Button, Form, Modal } from "react-bootstrap";
import { PencilSquare, Trash, PlusCircle } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";
import { useSettingsStore } from "../stores/useSettingsStore";

interface Setting {
  name: string;
  value: string;
}

export default function Settings() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [editValue, setEditValue] = useState("");
  const [isNew, setIsNew] = useState(true);
  const [saving, setSaving] = useState(false);
  const { fetchSettings: refreshTheme } = useSettingsStore();

  const fetchSettings = () => {
    axiosClient.get("/settings").then((res) => setSettings(res.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchSettings(); }, []);

  const handleAdd = () => { setIsNew(true); setEditName(""); setEditValue(""); setShowModal(true); };
  const handleEdit = (s: Setting) => { setIsNew(false); setEditName(s.name); setEditValue(s.value); setShowModal(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axiosClient.put("/settings", { name: editName, value: editValue });
      setShowModal(false);
      fetchSettings();
      // Refresh theme if color/title/label changed
      if (["navbar_color", "app_title", "instance_label"].includes(editName)) {
        refreshTheme();
      }
    } catch {} finally { setSaving(false); }
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete setting "${name}"?`)) return;
    try {
      // Use the settings upsert endpoint to set empty, or we need a delete endpoint
      // For now, the global settings don't have a delete endpoint — just set value to empty
      await axiosClient.put("/settings", { name, value: "" });
      fetchSettings();
    } catch {}
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h3 className="mb-0">Global Settings</h3>
          <small className="text-muted">Superuser only — these apply to all groups</small>
        </div>
        <Button variant="primary" size="sm" onClick={handleAdd}>
          <PlusCircle className="me-1" /> Add Setting
        </Button>
      </div>

      {loading ? <p className="text-muted">Loading...</p> : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr><th>Name</th><th>Value</th><th style={{ width: 90 }}>Actions</th></tr>
          </thead>
          <tbody>
            {settings.map((s) => (
              <tr key={s.name}>
                <td><code>{s.name}</code></td>
                <td>
                  {s.name === "navbar_color" ? (
                    <span>
                      {s.value}
                      <span
                        className="ms-2 d-inline-block rounded"
                        style={{ width: 16, height: 16, backgroundColor: `var(--theme-color-500, #666)`, verticalAlign: "middle" }}
                      />
                    </span>
                  ) : s.value}
                </td>
                <td>
                  <Button variant="outline-primary" size="sm" className="me-1" onClick={() => handleEdit(s)}><PencilSquare size={14} /></Button>
                  <Button variant="outline-danger" size="sm" onClick={() => handleDelete(s.name)}><Trash size={14} /></Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>{isNew ? "Add Setting" : "Edit Setting"}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3"><Form.Label>Name</Form.Label>
            <Form.Control value={editName} onChange={(e) => setEditName(e.target.value)} disabled={!isNew} placeholder="e.g., navbar_color" />
          </Form.Group>
          <Form.Group className="mb-3"><Form.Label>Value</Form.Label>
            {editName === "navbar_color" ? (
              <Form.Select value={editValue} onChange={(e) => setEditValue(e.target.value)}>
                {["slate","gray","zinc","stone","red","orange","amber","yellow","lime","green","emerald","teal","cyan","sky","blue","indigo","violet","purple","fuchsia","pink","rose"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Form.Select>
            ) : (
              <Form.Control value={editValue} onChange={(e) => setEditValue(e.target.value)} placeholder="Setting value" />
            )}
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || !editName}>{saving ? "Saving..." : "Save"}</Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}
