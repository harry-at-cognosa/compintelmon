import { useState, useEffect, FormEvent } from "react";
import { Modal, Form, Button } from "react-bootstrap";
import axiosClient from "../api/axiosClient";

interface Subject {
  gsubject_id: number;
  gsubject_name: string;
  gsubject_type: string;
  enabled: boolean;
}

interface SubjectType {
  subj_type_id: number;
  subj_type_name: string;
  subj_type_desc: string;
  subj_type_enabled: boolean;
}

interface Props {
  show: boolean;
  onHide: () => void;
  onSaved: () => void;
  subject?: Subject | null;
}

export default function SubjectFormModal({ show, onHide, onSaved, subject }: Props) {
  const [name, setName] = useState("");
  const [type, setType] = useState("company");
  const [enabled, setEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [subjectTypes, setSubjectTypes] = useState<SubjectType[]>([]);

  const isEdit = !!subject;

  // Fetch subject types from API
  useEffect(() => {
    if (show && subjectTypes.length === 0) {
      axiosClient
        .get("/subject-types")
        .then((res) => {
          const types = res.data.filter((t: SubjectType) => t.subj_type_enabled);
          setSubjectTypes(types);
          if (!subject && types.length > 0) {
            setType(types[0].subj_type_name);
          }
        })
        .catch(() => {});
    }
  }, [show]);

  useEffect(() => {
    if (subject) {
      setName(subject.gsubject_name);
      setType(subject.gsubject_type);
      setEnabled(subject.enabled);
    } else {
      setName("");
      if (subjectTypes.length > 0) {
        setType(subjectTypes[0].subj_type_name);
      }
      setEnabled(true);
    }
    setError("");
  }, [subject, show]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      if (isEdit) {
        await axiosClient.put(`/subjects/${subject!.gsubject_id}`, {
          gsubject_name: name,
          gsubject_type: type,
          enabled,
        });
      } else {
        await axiosClient.post("/subjects", {
          gsubject_name: name,
          gsubject_type: type,
          enabled,
        });
      }
      onSaved();
      onHide();
    } catch {
      setError("Failed to save subject. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <Modal.Title>{isEdit ? "Edit Subject" : "Add Subject"}</Modal.Title>
      </Modal.Header>
      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          {error && <div className="alert alert-danger py-2">{error}</div>}
          <Form.Group className="mb-3">
            <Form.Label>Subject Name</Form.Label>
            <Form.Control
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={1}
              maxLength={200}
              autoFocus
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Type</Form.Label>
            <Form.Select value={type} onChange={(e) => setType(e.target.value)}>
              {subjectTypes.map((t) => (
                <option key={t.subj_type_id} value={t.subj_type_name}>
                  {t.subj_type_name}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Check
              type="switch"
              label="Enabled"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? "Saving..." : isEdit ? "Save Changes" : "Create Subject"}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
