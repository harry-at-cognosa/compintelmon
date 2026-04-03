import { useEffect, useState } from "react";
import { Container, Table, Button, Form, Modal, Badge, Row, Col } from "react-bootstrap";
import { PencilSquare, PlusCircle } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";

interface ManagedUser {
  user_id: number;
  user_name: string;
  full_name: string;
  email: string;
  group_id: number;
  is_active: boolean;
  is_superuser: boolean;
  is_groupadmin: boolean;
  is_subjectmanager: boolean;
  last_seen: string | null;
}

interface Group {
  group_id: number;
  group_name: string;
}

export default function ManageUsers() {
  const auth = useAuthStore();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editUser, setEditUser] = useState<ManagedUser | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    user_name: "", full_name: "", email: "", password: "",
    group_id: auth.group_id, is_active: true, is_superuser: false,
    is_groupadmin: false, is_subjectmanager: false,
  });

  const fetchUsers = () => {
    axiosClient.get("/manage/users").then((r) => setUsers(r.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
    if (auth.is_superuser) {
      axiosClient.get("/groups").then((r) => setGroups(r.data)).catch(() => {});
    }
  }, []);

  const openAdd = () => {
    setEditUser(null);
    setForm({ user_name: "", full_name: "", email: "", password: "", group_id: auth.group_id, is_active: true, is_superuser: false, is_groupadmin: false, is_subjectmanager: false });
    setShowModal(true);
  };

  const openEdit = (u: ManagedUser) => {
    setEditUser(u);
    setForm({ user_name: u.user_name, full_name: u.full_name, email: u.email, password: "", group_id: u.group_id, is_active: u.is_active, is_superuser: u.is_superuser, is_groupadmin: u.is_groupadmin, is_subjectmanager: u.is_subjectmanager });
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editUser) {
        const update: Record<string, unknown> = {};
        if (form.full_name !== editUser.full_name) update.full_name = form.full_name;
        if (form.email !== editUser.email) update.email = form.email;
        if (form.is_active !== editUser.is_active) update.is_active = form.is_active;
        if (form.is_superuser !== editUser.is_superuser) update.is_superuser = form.is_superuser;
        if (form.is_groupadmin !== editUser.is_groupadmin) update.is_groupadmin = form.is_groupadmin;
        if (form.is_subjectmanager !== editUser.is_subjectmanager) update.is_subjectmanager = form.is_subjectmanager;
        if (form.group_id !== editUser.group_id) update.group_id = form.group_id;
        await axiosClient.put(`/manage/users/${editUser.user_id}`, update);
      } else {
        await axiosClient.post("/manage/users", form);
      }
      setShowModal(false);
      fetchUsers();
    } catch {} finally { setSaving(false); }
  };

  const roleLabel = (u: ManagedUser) => {
    if (u.is_superuser) return <Badge bg="danger">superuser</Badge>;
    if (u.is_groupadmin) return <Badge bg="warning" text="dark">groupadmin</Badge>;
    if (u.is_subjectmanager) return <Badge bg="info">subjectmanager</Badge>;
    return <Badge bg="secondary">user</Badge>;
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="mb-0">Manage Users</h3>
        <Button variant="primary" size="sm" onClick={openAdd}><PlusCircle className="me-1" />Add User</Button>
      </div>

      {loading ? <p className="text-muted">Loading...</p> : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr><th>#</th><th>Username</th><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th style={{ width: 60 }}></th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>{u.user_id}</td>
                <td><code>{u.user_name}</code></td>
                <td>{u.full_name}</td>
                <td><small>{u.email}</small></td>
                <td>{roleLabel(u)}</td>
                <td><Badge bg={u.is_active ? "success" : "danger"}>{u.is_active ? "Yes" : "No"}</Badge></td>
                <td><Button variant="outline-primary" size="sm" onClick={() => openEdit(u)}><PencilSquare size={14} /></Button></td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton><Modal.Title>{editUser ? "Edit User" : "Add User"}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-2"><Form.Label>Username</Form.Label>
            <Form.Control value={form.user_name} onChange={(e) => setForm({ ...form, user_name: e.target.value })} disabled={!!editUser} />
          </Form.Group>
          <Form.Group className="mb-2"><Form.Label>Full Name</Form.Label>
            <Form.Control value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </Form.Group>
          <Form.Group className="mb-2"><Form.Label>Email</Form.Label>
            <Form.Control type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Form.Group>
          {!editUser && (
            <Form.Group className="mb-2"><Form.Label>Password</Form.Label>
              <Form.Control type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </Form.Group>
          )}
          {auth.is_superuser && groups.length > 0 && (
            <Form.Group className="mb-2"><Form.Label>Group</Form.Label>
              <Form.Select value={form.group_id} onChange={(e) => setForm({ ...form, group_id: parseInt(e.target.value) })}>
                {groups.map((g) => <option key={g.group_id} value={g.group_id}>{g.group_name}</option>)}
              </Form.Select>
            </Form.Group>
          )}
          <hr />
          <Row>
            <Col><Form.Check type="switch" label="Active" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /></Col>
            <Col><Form.Check type="switch" label="Subject Manager" checked={form.is_subjectmanager} onChange={(e) => setForm({ ...form, is_subjectmanager: e.target.checked })} /></Col>
          </Row>
          <Row className="mt-2">
            <Col><Form.Check type="switch" label="Group Admin" checked={form.is_groupadmin} onChange={(e) => setForm({ ...form, is_groupadmin: e.target.checked })} /></Col>
            <Col>
              {auth.is_superuser && (
                <Form.Check type="switch" label="Superuser" checked={form.is_superuser} onChange={(e) => setForm({ ...form, is_superuser: e.target.checked })} />
              )}
            </Col>
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving || (!editUser && (!form.user_name || !form.email || !form.password))}>{saving ? "Saving..." : "Save"}</Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}
