import React, { useState } from 'react';
import { Form, Button, Alert, Container, Spinner } from 'react-bootstrap';
// import api from '../services/api'; // No longer needed directly
import { useAuth } from '../context/AuthContext'; // Import useAuth

// No longer needs onLoginSuccess prop
function Login() { 
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    // const [error, setError] = useState(''); // Get error from context
    const [loading, setLoading] = useState(false); // Local loading state for button

    // Get login function and error state from context
    const { login, authError } = useAuth(); 

    const handleSubmit = async (e) => {
        e.preventDefault();
        // setError(''); // Context handles error state
        setLoading(true);
        const success = await login(username, password);
        // If login fails, authError will be set in context
        if (!success) {
            setLoading(false); // Stop loading on failure
        }
        // On success, App component will re-render due to currentUser change in context
        // and this component will unmount.
    };

    return (
        <Container className="mt-5" style={{ maxWidth: '400px' }}>
            <h2>Login</h2>
            {/* Display error from context */} 
            {authError && <Alert variant="danger">{authError}</Alert>}
            <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3" controlId="formBasicUsername">
                    <Form.Label>Username</Form.Label>
                    <Form.Control 
                        type="text" 
                        placeholder="Enter username" 
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        disabled={loading} // Disable form while logging in
                    />
                </Form.Group>

                <Form.Group className="mb-3" controlId="formBasicPassword">
                    <Form.Label>Password</Form.Label>
                    <Form.Control 
                        type="password" 
                        placeholder="Password" 
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        disabled={loading} // Disable form while logging in
                    />
                </Form.Group>
                <Button variant="primary" type="submit" disabled={loading}>
                    {loading ? <><Spinner as="span" animation="border" size="sm"/> Logging in...</> : 'Login'}
                </Button>
            </Form>
        </Container>
    );
}

export default Login; 