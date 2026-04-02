import { useEffect, useState } from "react";
import { Container, Table, Button, Form, Modal } from "react-bootstrap";
import { PencilSquare, Trash, PlusCircle } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";

interface GroupSetting {
  group_id: number;
  name: string;
  value: string;
}

export default function GroupSettings() {
  const { group_id, group_name } = useAuthStore();
  const [settings, setSettings] = useState<GroupSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [editValue, setEditValue] = useState("");
  const [isNew, setIsNew] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchSettings = () => {
    axiosClient
      .get(`/group_settings/${group_id}`)
      .then((res) => setSettings(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSettings();
  }, [group_id]);

  const handleAdd = () => {
    setIsNew(true);
    setEditName("");
    setEditValue("");
    setShowModal(true);
  };

  const handleEdit = (s: GroupSetting) => {
    setIsNew(false);
    setEditName(s.name);
    setEditValue(s.value);
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axiosClient.put(`/group_settings/${group_id}`, {
        name: editName,
        value: editValue,
      });
      setShowModal(false);
      fetchSettings();
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete setting "${name}"?`)) return;
    try {
      await axiosClient.delete(`/group_settings/${group_id}/${name}`);
      fetchSettings();
    } catch {
      // handle error
    }
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h3 className="mb-0">Group Settings</h3>
          <small className="text-muted">Group: {group_name}</small>
        </div>
        <Button variant="primary" size="sm" onClick={handleAdd}>
          <PlusCircle className="me-1" /> Add Setting
        </Button>
      </div>

      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : settings.length === 0 ? (
        <p className="text-muted">No group settings configured.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>Name</th>
              <th>Value</th>
              <th style={{ width: 90 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {settings.map((s) => (
              <tr key={s.name}>
                <td><code>{s.name}</code></td>
                <td>{s.value}</td>
                <td>
                  <Button
                    variant="outline-primary"
                    size="sm"
                    className="me-1"
                    onClick={() => handleEdit(s)}
                  >
                    <PencilSquare size={14} />
                  </Button>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => handleDelete(s.name)}
                  >
                    <Trash size={14} />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{isNew ? "Add Setting" : "Edit Setting"}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Name</Form.Label>
            <Form.Control
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              disabled={!isNew}
              placeholder="e.g., enable_markdown_reports"
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Value</Form.Label>
            <Form.Control
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              placeholder="e.g., true"
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || !editName}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}
