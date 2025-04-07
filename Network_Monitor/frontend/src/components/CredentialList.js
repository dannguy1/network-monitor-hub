import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import CredentialForm from './CredentialForm';
// Import Card, Table, Button, Spinner, Alert, Badge, ButtonGroup
import { Card, Table, Button, Spinner, Alert, Badge, ButtonGroup } from 'react-bootstrap';
// Import Icons
import { PencilSquare, Trash } from 'react-bootstrap-icons';

function CredentialList() {
    const [credentials, setCredentials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingCredential, setEditingCredential] = useState(null);
    const [actionError, setActionError] = useState(null);
    const [actionMessage, setActionMessage] = useState(null);
    const [associatedDevices, setAssociatedDevices] = useState({}); // { credId: deviceName }

    // Fetch both credentials and devices (to show associated device names)
    const fetchData = useCallback(() => {
        setLoading(true);
        setError(null);
        Promise.all([api.getCredentials(), api.getDevices()])
            .then(([credResponse, deviceResponse]) => {
                const creds = credResponse.data || [];
                const devices = deviceResponse.data || [];
                setCredentials(creds);

                // Create a map of credentialId -> deviceName
                const deviceMap = {};
                devices.forEach(device => {
                    if (device.credential_id) {
                        deviceMap[device.credential_id] = device.name;
                    }
                });
                setAssociatedDevices(deviceMap);

                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching data:", err);
                setError(err.response?.data?.error || err.message || 'Failed to fetch data');
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const clearMessages = () => {
        setActionError(null);
        setActionMessage(null);
    };

    const handleCreate = (formData) => {
        clearMessages();
        api.createCredential(formData)
            .then(() => {
                setActionMessage(`Credential '${formData.name}' created successfully.`);
                fetchData(); // Refetch both creds and devices
                setShowForm(false);
            })
            .catch(err => {
                console.error("Error creating credential:", err);
                setActionError(err.response?.data?.error || err.message || 'Failed to create credential');
            });
    };

    const handleUpdate = (formData) => {
        clearMessages();
        if (!editingCredential) return;
        api.updateCredential(editingCredential.id, formData)
            .then(() => {
                setActionMessage(`Credential '${formData.name}' updated successfully.`);
                fetchData(); // Refetch both creds and devices
                setShowForm(false);
                setEditingCredential(null);
            })
            .catch(err => {
                console.error("Error updating credential:", err);
                setActionError(err.response?.data?.error || err.message || 'Failed to update credential');
            });
    };

    const handleDelete = (credential) => {
        clearMessages();
        const deviceName = associatedDevices[credential.id];
        const confirmMessage = deviceName
            ? `This credential is associated with device '${deviceName}'. Deleting it will disassociate it. Are you sure you want to delete credential '${credential.name}'?`
            : `Are you sure you want to delete credential '${credential.name}'? This cannot be undone.`;

        if (window.confirm(confirmMessage)) {
            api.deleteCredential(credential.id)
                .then(() => {
                    setActionMessage(`Credential '${credential.name}' deleted successfully.`);
                    fetchData(); // Refetch both creds and devices
                })
                .catch(err => {
                    console.error("Error deleting credential:", err);
                    let errMsg = err.response?.data?.error || err.message || 'Failed to delete credential';
                    // Backend might still send device_name even if we check frontend-side
                    if (err.response?.data?.device_name) {
                        errMsg += ` (Associated with device: ${err.response.data.device_name})`;
                    }
                    setActionError(errMsg);
                });
        }
    };

    const openEditForm = (credential) => {
        clearMessages();
        setEditingCredential(credential);
        setShowForm(true);
    };

    const openCreateForm = () => {
        clearMessages();
        setEditingCredential(null);
        setShowForm(true);
    };

    const handleCancelForm = () => {
        setShowForm(false);
        setEditingCredential(null);
        // Don't clear messages on cancel
    };

    // Show main loading spinner only on initial load
    if (loading && credentials.length === 0) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '200px' }}>
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading Credentials...</span>
                </Spinner>
            </div>
        );
    }

    // Show primary error only if loading fails completely
    if (error && credentials.length === 0) {
        return <Alert variant="danger">Error loading credentials: {error}</Alert>;
    }

    return (
        <Card>
            <Card.Header className="d-flex justify-content-between align-items-center">
                 <h4 className="mb-0">SSH Credentials</h4>
                 <Button variant="primary" onClick={openCreateForm}>
                     Add New Credential
                 </Button>
             </Card.Header>
            <Card.Body>
                {/* Display Action Feedback */}
                {actionError && <Alert variant="danger" onClose={() => setActionError(null)} dismissible>{actionError}</Alert>}
                {actionMessage && <Alert variant="success" onClose={() => setActionMessage(null)} dismissible>{actionMessage}</Alert>}

                {/* Display Form Conditionally */} 
                {showForm && (
                    <Card className="mb-4">
                        <Card.Body>
                             <CredentialForm
                                 initialCredential={editingCredential}
                                 onSubmit={editingCredential ? handleUpdate : handleCreate}
                                 onCancel={handleCancelForm}
                             />
                        </Card.Body>
                    </Card>
                 )}

                {/* Display Loading/Error for Refresh */} 
                {loading && credentials.length > 0 && <Spinner animation="border" size="sm" className="me-2" />} {/* Indicate refresh */}
                {error && <Alert variant="warning">Could not refresh credential list: {error}</Alert>} {/* Non-critical error */}

                {/* Credential Table */} 
                <Table striped bordered hover responsive className="mt-3 align-middle">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>SSH Username</th>
                            <th>Auth Type</th>
                            <th>Associated Device</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {credentials.length === 0 && !loading ? (
                            <tr>
                                <td colSpan="6" className="text-center">No credentials configured yet.</td>
                            </tr>
                        ) : (
                            credentials.map(cred => (
                                <tr key={cred.id}>
                                    <td>{cred.name}</td>
                                    <td>{cred.ssh_username}</td>
                                    <td>
                                        <Badge bg={cred.auth_type === 'password' ? 'info' : 'secondary'} text="dark">
                                            {cred.auth_type === 'password' ? 'Password' : 'Private Key'}
                                        </Badge>
                                    </td>
                                     <td>{associatedDevices[cred.id] || '-'}</td>
                                    <td>{new Date(cred.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <ButtonGroup size="sm">
                                            <Button variant="outline-secondary" onClick={() => openEditForm(cred)} title="Edit Credential">
                                                <PencilSquare />
                                            </Button>
                                            <Button variant="outline-danger" onClick={() => handleDelete(cred)} title="Delete Credential">
                                                 <Trash />
                                             </Button>
                                        </ButtonGroup>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </Table>
            </Card.Body>
        </Card>
    );
}

export default CredentialList; 