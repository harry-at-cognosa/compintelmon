import { Modal, Button } from "react-bootstrap";

interface Props {
  show: boolean;
  onHide: () => void;
  onConfirm: () => void;
  itemName: string;
  loading?: boolean;
}

export default function ConfirmDeleteModal({ show, onHide, onConfirm, itemName, loading }: Props) {
  return (
    <Modal show={show} onHide={onHide} centered>
      <Modal.Header closeButton>
        <Modal.Title>Confirm Delete</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        Are you sure you want to delete <strong>{itemName}</strong>? This action cannot be undone.
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} disabled={loading}>
          {loading ? "Deleting..." : "Delete"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
