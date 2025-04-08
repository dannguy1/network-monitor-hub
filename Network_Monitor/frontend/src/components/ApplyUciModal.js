import React, { useState } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import api from '../services/api';

function ApplyUciModal({ device, onSubmit, onCancel }) {
    const [uciCommands, setUciCommands] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        setLoading(true);

        // Split commands by newline, filter out empty lines/comments
        const commandsArray = uciCommands
            .split('\n')
            .map(cmd => cmd.trim())
            .filter(cmd => cmd && !cmd.startsWith('#'));

        if (commandsArray.length === 0) {
            setError("Please enter at least one valid UCI command.");
            setLoading(false);
            return;
        }

        try {
            // Call the CORRECT API function: applyUciToDevice
            await api.applyUciToDevice(device.id, commandsArray);
            onSubmit(); // Call the prop passed down from DeviceList
        } catch (err) {
            console.error("Error applying UCI commands via modal:", err);
            const errMsg = err.response?.data?.stderr || err.response?.data?.error || err.message || 'Failed to apply commands';
            setError(errMsg);
            // Do not call onSubmit() on error, keep modal open
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal show={true} onHide={onCancel} backdrop="static" keyboard={false}>
            <Modal.Header closeButton>
                <Modal.Title>Apply UCI Commands to {device.name}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {error && <Alert variant="danger">{error}</Alert>}
                <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                        <Form.Label>UCI Commands</Form.Label>
                        <Form.Control
                            as="textarea"
                            rows={10}
                            placeholder="Example:\nset system.@system[0].hostname='MyNewHostname'\nset network.lan.ipaddr='192.168.2.1'\n# uci commit system \n# uci commit network \nreboot"
                            value={uciCommands}
                            onChange={(e) => setUciCommands(e.target.value)}
                            disabled={loading}
                        />
                        <Form.Text className="text-muted">
                            Enter UCI commands to be executed sequentially. Lines starting with # are ignored.
                            Remember to include {'`uci commit <config>`'} if needed.
                        </Form.Text>
                    </Form.Group>
                    <div className="d-flex justify-content-end">
                        <Button variant="secondary" onClick={onCancel} disabled={loading} className="me-2">
                            Cancel
                        </Button>
                        <Button variant="primary" type="submit" disabled={loading}>
                            {loading ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Applying...</> : 'Apply Commands'}
                        </Button>
                    </div>
                </Form>
            </Modal.Body>
        </Modal>
    );
}

export default ApplyUciModal; 