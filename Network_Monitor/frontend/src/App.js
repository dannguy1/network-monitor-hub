import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Link,
    NavLink
} from 'react-router-dom';
import { Navbar, Container, Nav, Button, Spinner } from 'react-bootstrap';
import './App.css';
import DeviceList from './components/DeviceList';
import LogList from './components/LogList';
import CredentialList from './components/CredentialList';
import Login from './components/Login';
import { useAuth } from './context/AuthContext';

function App() {
    const { currentUser, loadingAuth, logout } = useAuth();

    const navLinkStyle = ({ isActive }) => ({
        fontWeight: isActive ? 'bold' : 'normal',
    });

    if (loadingAuth) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
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
            <div className="App">
                <Navbar bg="dark" variant="dark" expand="lg" sticky="top">
                    <Container>
                        <Navbar.Brand as={Link} to="/">Network Monitor</Navbar.Brand>
                        <Navbar.Toggle aria-controls="basic-navbar-nav" />
                        <Navbar.Collapse id="basic-navbar-nav">
                            <Nav className="me-auto">
                                <Nav.Link as={NavLink} to="/" style={navLinkStyle} end>Devices</Nav.Link>
                                <Nav.Link as={NavLink} to="/credentials" style={navLinkStyle}>Credentials</Nav.Link>
                                <Nav.Link as={NavLink} to="/logs" style={navLinkStyle}>Logs</Nav.Link>
                            </Nav>
                            <Nav>
                                <Navbar.Text className="me-2">Signed in as: {currentUser.username}</Navbar.Text>
                                <Button variant="outline-secondary" size="sm" onClick={logout}>Logout</Button>
                            </Nav>
                        </Navbar.Collapse>
                    </Container>
                </Navbar>

                <main className="container mt-4">
                    <Routes>
                        <Route path="/" element={<DeviceList />} />
                        <Route path="/credentials" element={<CredentialList />} />
                        <Route path="/logs" element={<LogList />} />
                        <Route path="*" element={<DeviceList />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}

export default App;
