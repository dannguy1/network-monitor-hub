import React, { useState, useEffect } from 'react';
import { Form, Button, Col, Row, Alert } from 'react-bootstrap'; // Import Bootstrap components

function DeviceForm({ initialDevice, onSubmit, onCancel }) {
    const isEditing = !!initialDevice;
    const [formData, setFormData] = useState({
        name: '',
        ip_address: '',
        description: '',
        // Credential fields
        credential_ssh_username: '',
        credential_auth_type: 'password', 
        credential_password: '',
        credential_private_key: ''
    });
    const [validationError, setValidationError] = useState('');

    useEffect(() => {
        if (initialDevice) {
            // When editing, only set device-specific fields
            setFormData(prev => {
                const updated = { 
                    ...prev, // Keep previous state (incl. default cred fields)
                    name: initialDevice.name || '',
                    ip_address: initialDevice.ip_address || '',
                    description: initialDevice.description || ''
                    // Do NOT reset credential fields here
                };
                return updated;
            });
        } else {
            // Reset form for creation (keep this block)
            const resetData = {
                name: '', ip_address: '', description: '',
                credential_ssh_username: '', credential_auth_type: 'password',
                credential_password: '', credential_private_key: ''
            };
            setFormData(resetData);
        }
        setValidationError(''); // Clear errors on form load/reset
    }, [initialDevice]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        setValidationError(''); // Clear previous errors

        // Basic device validation
        if (!formData.name || !formData.ip_address) {
            setValidationError('Device Name and IP Address are required.');
            return;
        }

        // Credential validation only when CREATING
        if (!isEditing) {
            if (!formData.credential_ssh_username || !formData.credential_auth_type) {
                setValidationError('SSH Username and Auth Type are required when creating a device.');
                return;
            }
            if (formData.credential_auth_type === 'password' && !formData.credential_password) {
                setValidationError('Password is required for password authentication.');
                return;
            }
            if (formData.credential_auth_type === 'key' && !formData.credential_private_key) {
                setValidationError('Private Key is required for key authentication.');
                return;
            }
        }
        
        // Prepare data to send (exclude credential fields if editing)
        const dataToSend = {
            name: formData.name,
            ip_address: formData.ip_address,
            description: formData.description
        };
        if (!isEditing) {
             Object.assign(dataToSend, {
                credential_ssh_username: formData.credential_ssh_username,
                credential_auth_type: formData.credential_auth_type,
                credential_password: formData.credential_password,
                credential_private_key: formData.credential_private_key
             });
        }

        onSubmit(dataToSend); // Pass the potentially combined data
    };

    return (
        <Form onSubmit={handleSubmit} className="mb-4 p-3 border rounded bg-light">
            <h3>{isEditing ? 'Edit Device' : 'Add New Device'}</h3>
            {validationError && <Alert variant="danger">{validationError}</Alert>}
            <Row className="mb-3">
                <Form.Group as={Col} controlId="formDeviceName">
                    <Form.Label>Device Name*</Form.Label>
                    <Form.Control
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleChange}
                        required
                    />
                </Form.Group>
                <Form.Group as={Col} controlId="formDeviceIp">
                    <Form.Label>IP Address*</Form.Label>
                    <Form.Control
                        type="text"
                        name="ip_address"
                        value={formData.ip_address}
                        onChange={handleChange}
                        required
                    />
                </Form.Group>
            </Row>
            <Form.Group className="mb-3" controlId="formDeviceDescription">
                <Form.Label>Description</Form.Label>
                <Form.Control
                    as="textarea"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows={2}
                />
            </Form.Group>

            {!isEditing && (
                <>
                    <hr />
                    <h4>Device Credentials (Required)</h4>
                     <Row className="mb-3">
                        <Form.Group as={Col} controlId="formCredSshUser">
                            <Form.Label>SSH Username*</Form.Label>
                            <Form.Control
                                type="text"
                                name="credential_ssh_username"
                                value={formData.credential_ssh_username}
                                onChange={handleChange}
                                required
                            />
                        </Form.Group>
                    </Row>
                     <Form.Group className="mb-3" controlId="formCredAuthType">
                        <Form.Label>Authentication Type*</Form.Label>
                        <Form.Select
                            name="credential_auth_type"
                            value={formData.credential_auth_type}
                            onChange={handleChange}
                            required
                        >
                            <option value="password">Password</option>
                            <option value="key">Private Key</option>
                        </Form.Select>
                    </Form.Group>

                    {formData.credential_auth_type === 'password' ? (
                        <Form.Group className="mb-3" controlId="formCredPassword">
                            <Form.Label>Password*</Form.Label>
                            <Form.Control
                                type="password"
                                name="credential_password"
                                value={formData.credential_password}
                                onChange={handleChange}
                                required
                            />
                        </Form.Group>
                    ) : (
                        <Form.Group className="mb-3" controlId="formCredPrivateKey">
                            <Form.Label>Private Key*</Form.Label>
                            <Form.Control
                                as="textarea"
                                name="credential_private_key"
                                value={formData.credential_private_key}
                                onChange={handleChange}
                                rows={5}
                                required
                                placeholder="Paste private key here (e.g., -----BEGIN RSA PRIVATE KEY-----...)"
                            />
                        </Form.Group>
                    )}
                </>
            )}

            <div className="d-flex justify-content-end">
                <Button variant="secondary" onClick={onCancel} className="me-2">
                    Cancel
                </Button>
                 <Button variant="primary" type="submit">
                    {isEditing ? 'Update Device' : 'Create Device'}
                </Button>
            </div>
        </Form>
    );
}

export default DeviceForm; 