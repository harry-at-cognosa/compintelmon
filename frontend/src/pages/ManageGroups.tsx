import { useEffect, useState } from "react";
import { Container, Table, Button, Form, Modal, Badge } from "react-bootstrap";
import { PencilSquare, PlusCircle } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";

interface Group {
  group_id: number;
  group_name: string;
  is_active: boolean;
  deleted: number;
  created_at: string;
}

export default function ManageGroups() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editGroup, setEditGroup] = useState<Group | null>(null);
  const [name, setName] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchGroups = () => {
    axiosClient.get("/groups").then((r) => setGroups(r.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchGroups(); }, []);

  const openAdd = () => { setEditGroup(null); setName(""); setIsActive(true); setShowModal(true); };
  const openEdit = (g: Group) => { setEditGroup(g); setName(g.group_name); setIsActive(g.is_active); setShowModal(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editGroup) {
        await axiosClient.put(`/groups/${editGroup.group_id}`, { group_name: name, is_active: isActive });
      } else {
        await axiosClient.post("/groups", { group_name: name });
      }
      setShowModal(false);
      fetchGroups();
    } catch {} finally { setSaving(false); }
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="mb-0">Manage Groups</h3>
        <Button variant="primary" size="sm" onClick={openAdd}><PlusCircle className="me-1" />Add Group</Button>
      </div>

      {loading ? <p className="text-muted">Loading...</p> : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr><th>#</th><th>Name</th><th>Active</th><th>Created</th><th style={{ width: 60 }}></th></tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.group_id}>
                <td>{g.group_id}</td>
                <td>{g.group_name}</td>
                <td><Badge bg={g.is_active ? "success" : "danger"}>{g.is_active ? "Active" : "Inactive"}</Badge></td>
                <td><small>{new Date(g.created_at).toLocaleDateString()}</small></td>
                <td><Button variant="outline-primary" size="sm" onClick={() => openEdit(g)}><PencilSquare size={14} /></Button></td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>{editGroup ? "Edit Group" : "Add Group"}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3"><Form.Label>Group Name</Form.Label>
            <Form.Control value={name} onChange={(e) => setName(e.target.value)} required />
          </Form.Group>
          {editGroup && (
            <Form.Group><Form.Check type="switch" label="Active" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /></Form.Group>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || !name}>{saving ? "Saving..." : "Save"}</Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}
