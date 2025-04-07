import React, { useState, useEffect } from 'react';

function CredentialForm({ initialCredential, onSubmit, onCancel }) {
    const [formData, setFormData] = useState({
        name: '',
        ssh_username: '',
        auth_type: 'password', // Default to password
        password: '',
        private_key: ''
    });

    useEffect(() => {
        if (initialCredential) {
            // Note: We don't receive decrypted password/key from the backend for editing
            // We only get flags like has_password/has_private_key.
            // The form will allow *replacing* the existing password/key.
            setFormData({
                name: initialCredential.name || '',
                ssh_username: initialCredential.ssh_username || '',
                auth_type: initialCredential.auth_type || 'password',
                password: '', // Clear password field on edit
                private_key: '' // Clear key field on edit
            });
        } else {
            // Reset form for creation
            setFormData({
                name: '',
                ssh_username: '',
                auth_type: 'password',
                password: '',
                private_key: ''
            });
        }
    }, [initialCredential]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!formData.name || !formData.ssh_username) {
            alert('Name and SSH Username are required.');
            return;
        }
        if (formData.auth_type === 'password' && !initialCredential && !formData.password) {
            alert('Password is required when creating with password authentication.');
            return;
        }
        if (formData.auth_type === 'key' && !initialCredential && !formData.private_key) {
            alert('Private Key is required when creating with key authentication.');
            return;
        }
        // If editing, only send password/key if user entered something new
        const dataToSend = { ...formData };
        if (initialCredential) {
            if (!dataToSend.password) delete dataToSend.password;
            if (!dataToSend.private_key) delete dataToSend.private_key;
        }

        onSubmit(dataToSend);
    };

    return (
        <form onSubmit={handleSubmit} style={{ border: '1px dashed #ccc', padding: '15px', marginBottom: '15px' }}>
            <h3>{initialCredential ? 'Edit Credential' : 'Add New Credential'}</h3>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="cred_name">Name: </label>
                <input
                    type="text"
                    id="cred_name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                />
            </div>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="ssh_username">SSH Username: </label>
                <input
                    type="text"
                    id="ssh_username"
                    name="ssh_username"
                    value={formData.ssh_username}
                    onChange={handleChange}
                    required
                />
            </div>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="auth_type">Auth Type: </label>
                <select
                    id="auth_type"
                    name="auth_type"
                    value={formData.auth_type}
                    onChange={handleChange}
                >
                    <option value="password">Password</option>
                    <option value="key">Private Key</option>
                </select>
            </div>

            {formData.auth_type === 'password' && (
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="password">Password: </label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        placeholder={initialCredential ? "Enter new password to change" : ""}
                    />
                     {initialCredential && <small style={{ marginLeft: '10px' }}>(Leave blank to keep existing)</small>}
                </div>
            )}

            {formData.auth_type === 'key' && (
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="private_key">Private Key: </label>
                    <textarea
                        id="private_key"
                        name="private_key"
                        value={formData.private_key}
                        onChange={handleChange}
                        rows="5"
                        style={{ width: '90%', fontFamily: 'monospace' }}
                        placeholder={initialCredential ? "Paste new private key to change" : "Paste private key here (e.g., -----BEGIN RSA PRIVATE KEY-----...)"}
                    />
                     {initialCredential && <small style={{ display: 'block' }}>(Leave blank to keep existing)</small>}
                </div>
            )}

            <button type="submit" style={{ marginRight: '10px' }}>
                {initialCredential ? 'Update Credential' : 'Create Credential'}
            </button>
            <button type="button" onClick={onCancel}>
                Cancel
            </button>
        </form>
    );
}

export default CredentialForm; 