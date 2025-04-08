import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    NavLink,
    Navigate
} from 'react-router-dom';
import { Navbar, Container, Nav, Button, Spinner, Row, Col } from 'react-bootstrap';
import './App.css';
import Dashboard from './components/Dashboard';
import DeviceList from './components/DeviceList';
import LogList from './components/LogList';
import Login from './components/Login';
import { useAuth } from './context/AuthContext';
import { Speedometer2, HouseDoorFill, FileEarmarkTextFill } from 'react-bootstrap-icons';

function App() {
    const { currentUser, loadingAuth, logout } = useAuth();

    const navLinkStyle = ({ isActive }) => ({
        color: isActive ? 'white' : 'rgba(255, 255, 255, 0.7)',
        backgroundColor: isActive ? '#495057' : 'transparent',
        display: 'flex',
        alignItems: 'center',
        padding: '0.75rem 1rem',
        marginBottom: '0.25rem',
        borderRadius: '0.25rem',
    });

    const IconStyle = {
        marginRight: '10px',
        width: '20px',
    };

    if (loadingAuth) {
        return (
            <div className="d-flex justify-content-center align-items-center vh-100">
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                </Spinner>
            </div>
        );
    }

    if (!currentUser) {
        return <Login />;
    }

    return (
        <Router>
            <Navbar bg="dark" variant="dark" expand={false} className="top-navbar">
                <Container fluid>
                    <Navbar.Brand href="#home">Network Monitor</Navbar.Brand>
                    <Nav className="ms-auto flex-row align-items-center">
                        <Navbar.Text className="me-3 text-white">
                            Signed in as: {currentUser.username}
                        </Navbar.Text>
                        <Button variant="outline-secondary" size="sm" onClick={logout}>Logout</Button>
                    </Nav>
                </Container>
            </Navbar>

            <Container fluid className="h-100">
                <Row className="h-100">
                    <Col md={2} lg={2} className="bg-dark sidebar d-none d-md-block">
                        <Nav className="flex-column pt-3">
                            <Nav.Link as={NavLink} to="/dashboard" style={navLinkStyle}>
                                <Speedometer2 style={IconStyle} /> Dashboard
                            </Nav.Link>
                            <Nav.Link as={NavLink} to="/devices" style={navLinkStyle} end>
                                <HouseDoorFill style={IconStyle} /> Devices
                            </Nav.Link>
                            <Nav.Link as={NavLink} to="/logs" style={navLinkStyle}>
                                <FileEarmarkTextFill style={IconStyle} /> Logs
                            </Nav.Link>
                        </Nav>
                    </Col>

                    <Col md={10} lg={10} className="main-content p-4">
                        <Routes>
                            <Route path="/dashboard" element={<Dashboard />} />
                            <Route path="/devices" element={<DeviceList />} />
                            <Route path="/logs" element={<LogList />} />
                            <Route path="/" element={<Navigate replace to="/dashboard" />} />
                            <Route path="*" element={<Navigate replace to="/dashboard" />} />
                        </Routes>
                    </Col>
                </Row>
            </Container>
        </Router>
    );
}

export default App;
