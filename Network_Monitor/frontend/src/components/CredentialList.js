import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import CredentialForm from './CredentialForm';

function CredentialList() {
    const [credentials, setCredentials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingCredential, setEditingCredential] = useState(null);
    const [actionError, setActionError] = useState(null);
    const [actionMessage, setActionMessage] = useState(null);

    const fetchCredentials = useCallback(() => {
        setLoading(true);
        setError(null);
        api.getCredentials()
            .then(response => {
                setCredentials(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching credentials:", err);
                setError(err.response?.data?.error || err.message || 'Failed to fetch credentials');
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        fetchCredentials();
    }, [fetchCredentials]);

    const clearMessages = () => {
        setActionError(null);
        setActionMessage(null);
    };

    const handleCreate = (formData) => {
        clearMessages();
        api.createCredential(formData)
            .then(() => {
                setActionMessage(`Credential '${formData.name}' created successfully.`);
                fetchCredentials();
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
                fetchCredentials();
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
        if (window.confirm(`Are you sure you want to delete credential '${credential.name}'? This cannot be undone.`)) {
            api.deleteCredential(credential.id)
                .then(() => {
                    setActionMessage(`Credential '${credential.name}' deleted successfully.`);
                    fetchCredentials();
                })
                .catch(err => {
                    console.error("Error deleting credential:", err);
                    // Display specific error if credential is in use
                    let errMsg = err.response?.data?.error || err.message || 'Failed to delete credential';
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
        clearMessages();
    };

    if (loading) return <p>Loading credentials...</p>;
    if (error) return <p style={{ color: 'red' }}>Error loading credentials: {error}</p>;

    return (
        <div>
            <h2>Credentials</h2>
            {actionError && <p style={{ color: 'red' }}>Action Error: {actionError}</p>}
            {actionMessage && <p style={{ color: 'green' }}>{actionMessage}</p>}

            {!showForm && (
                 <button onClick={openCreateForm} style={{ marginBottom: '15px' }}>
                     Add New Credential
                 </button>
            )}

            {showForm && (
                <CredentialForm
                    initialCredential={editingCredential}
                    onSubmit={editingCredential ? handleUpdate : handleCreate}
                    onCancel={handleCancelForm}
                />
            )}

            {credentials.length === 0 && !loading ? (
                <p>No credentials found.</p>
            ) : (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {credentials.map(cred => (
                        <li key={cred.id} style={{ border: '1px solid #ccc', marginBottom: '10px', padding: '10px' }}>
                            <strong>{cred.name}</strong>
                            <br />
                            Username: {cred.ssh_username}
                            <br />
                            Auth Type: {cred.auth_type}
                            <br />
                            <small>Created: {new Date(cred.created_at).toLocaleString()}</small>
                            {cred.device_id && <small style={{ marginLeft: '15px' }}>(Associated with Device ID: {cred.device_id})</small>}
                            <br />
                            <div style={{ marginTop: '5px' }}>
                                 <button onClick={() => openEditForm(cred)} style={{ marginRight: '5px' }}>Edit</button>
                                 <button onClick={() => handleDelete(cred)} style={{ color: 'red' }}>Delete</button>
                                 {/* Add 'Verify' button later, maybe needs device context */} 
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default CredentialList; 