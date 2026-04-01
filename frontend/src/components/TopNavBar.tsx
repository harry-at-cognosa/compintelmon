import { Navbar, Nav, NavDropdown, Badge, Container } from "react-bootstrap";
import { LinkContainer } from "react-router-bootstrap";
import { useAuthStore } from "../stores/useAuthStore";
import { useSettingsStore } from "../stores/useSettingsStore";

export default function TopNavBar() {
  const auth = useAuthStore();
  const { app_title, instance_label } = useSettingsStore();

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="px-3">
      <Container fluid>
        <LinkContainer to="/app">
          <Navbar.Brand>
            {app_title}
            {instance_label && (
              <>
                {" "}
                <Badge bg="info" className="ms-2" style={{ fontSize: "0.7em" }}>
                  {instance_label}
                </Badge>
              </>
            )}
          </Navbar.Brand>
        </LinkContainer>

        <Navbar.Toggle aria-controls="main-navbar" />
        <Navbar.Collapse id="main-navbar">
          <Nav className="me-auto">
            <LinkContainer to="/app">
              <Nav.Link>Dashboard</Nav.Link>
            </LinkContainer>
            <LinkContainer to="/app/subjects">
              <Nav.Link>Subjects</Nav.Link>
            </LinkContainer>

            {auth.is_superuser && (
              <NavDropdown title="Admin" id="admin-dropdown">
                <LinkContainer to="/app/su/settings">
                  <NavDropdown.Item>Global Settings</NavDropdown.Item>
                </LinkContainer>
              </NavDropdown>
            )}
          </Nav>

          <Nav>
            <NavDropdown
              title={auth.user_name || "User"}
              id="user-dropdown"
              align="end"
            >
              <NavDropdown.ItemText className="text-muted" style={{ fontSize: "0.85em" }}>
                {auth.email}
                <br />
                Group: {auth.group_name}
              </NavDropdown.ItemText>
              <NavDropdown.Divider />
              <LinkContainer to="/app/logout">
                <NavDropdown.Item>Logout</NavDropdown.Item>
              </LinkContainer>
            </NavDropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}
