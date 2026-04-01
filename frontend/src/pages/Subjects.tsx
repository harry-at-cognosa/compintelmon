import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Container, Table, Badge, Button } from "react-bootstrap";
import { PencilSquare, Trash } from "react-bootstrap-icons";
import axiosClient from "../api/axiosClient";
import { useAuthStore } from "../stores/useAuthStore";
import SubjectFormModal from "../components/SubjectFormModal";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";

interface Subject {
  gsubject_id: number;
  gsubject_name: string;
  gsubject_type: string;
  gsubject_status: string;
  enabled: boolean;
}

export default function Subjects() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editSubject, setEditSubject] = useState<Subject | null>(null);
  const [deleteSubject, setDeleteSubject] = useState<Subject | null>(null);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  const auth = useAuthStore();
  const canManage = auth.is_subjectmanager || auth.is_groupadmin || auth.is_superuser;

  const fetchSubjects = () => {
    axiosClient
      .get("/subjects")
      .then((res) => setSubjects(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  const handleEdit = (e: React.MouseEvent, subject: Subject) => {
    e.stopPropagation();
    setEditSubject(subject);
    setShowForm(true);
  };

  const handleDeleteClick = (e: React.MouseEvent, subject: Subject) => {
    e.stopPropagation();
    setDeleteSubject(subject);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteSubject) return;
    setDeleting(true);
    try {
      await axiosClient.delete(`/subjects/${deleteSubject.gsubject_id}`);
      setDeleteSubject(null);
      fetchSubjects();
    } catch {
      // handle error
    } finally {
      setDeleting(false);
    }
  };

  const handleRowClick = (subject: Subject) => {
    navigate(`/app/subjects/${subject.gsubject_id}`);
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h3 className="mb-0">Subjects</h3>
        {canManage && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setEditSubject(null);
              setShowForm(true);
            }}
          >
            + Add Subject
          </Button>
        )}
      </div>

      {loading ? (
        <p className="text-muted">Loading...</p>
      ) : subjects.length === 0 ? (
        <p className="text-muted">No subjects configured yet.</p>
      ) : (
        <Table striped bordered hover size="sm">
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Enabled</th>
              {canManage && <th style={{ width: 90 }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {subjects.map((s) => (
              <tr
                key={s.gsubject_id}
                onClick={() => handleRowClick(s)}
                style={{ cursor: "pointer" }}
              >
                <td>{s.gsubject_id}</td>
                <td>{s.gsubject_name}</td>
                <td>
                  <Badge bg="secondary">{s.gsubject_type}</Badge>
                </td>
                <td>{s.gsubject_status}</td>
                <td>
                  <Badge bg={s.enabled ? "success" : "secondary"}>
                    {s.enabled ? "Yes" : "No"}
                  </Badge>
                </td>
                {canManage && (
                  <td>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      className="me-1"
                      onClick={(e) => handleEdit(e, s)}
                      title="Edit"
                    >
                      <PencilSquare size={14} />
                    </Button>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={(e) => handleDeleteClick(e, s)}
                      title="Delete"
                    >
                      <Trash size={14} />
                    </Button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <SubjectFormModal
        show={showForm}
        onHide={() => setShowForm(false)}
        onSaved={fetchSubjects}
        subject={editSubject}
      />

      <ConfirmDeleteModal
        show={!!deleteSubject}
        onHide={() => setDeleteSubject(null)}
        onConfirm={handleDeleteConfirm}
        itemName={deleteSubject?.gsubject_name || ""}
        loading={deleting}
      />
    </Container>
  );
}
