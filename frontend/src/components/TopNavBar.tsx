import { Navbar, Nav, NavDropdown, Badge, Container } from "react-bootstrap";
import { LinkContainer } from "react-router-bootstrap";
import { useAuthStore } from "../stores/useAuthStore";
import { useSettingsStore } from "../stores/useSettingsStore";

const NAVBAR_COLORS: Record<string, string> = {
  slate: "#334155",
  gray: "#374151",
  zinc: "#27272a",
  stone: "#292524",
  red: "#991b1b",
  orange: "#9a3412",
  amber: "#92400e",
  yellow: "#854d0e",
  lime: "#3f6212",
  green: "#166534",
  emerald: "#065f46",
  teal: "#115e59",
  cyan: "#155e75",
  sky: "#075985",
  blue: "#1e40af",
  indigo: "#3730a3",
  violet: "#5b21b6",
  purple: "#6b21a8",
  fuchsia: "#86198f",
  pink: "#9d174d",
  rose: "#9f1239",
};

export default function TopNavBar() {
  const auth = useAuthStore();
  const { app_title, instance_label, navbar_color } = useSettingsStore();
  const bgColor = NAVBAR_COLORS[navbar_color] || NAVBAR_COLORS.slate;

  return (
    <Navbar variant="dark" expand="lg" className="px-3" style={{ backgroundColor: bgColor }}>
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
