import React, { useState } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import api from '../services/api';

function ApplyUciModal({ device, onSubmit, onCancel }) {
    const [uciCommands, setUciCommands] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [commandOutput, setCommandOutput] = useState(null);

    const handleClose = () => {
        setUciCommands('');
        setError(null);
        setCommandOutput(null);
        setLoading(false);
        onCancel();
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        setCommandOutput(null);
        setLoading(true);

        const commandsArray = uciCommands
            .split('\n')
            .map(cmd => cmd.trim())
            .filter(cmd => cmd && !cmd.startsWith('#'));

        if (commandsArray.length === 0) {
            setError("Please enter at least one valid command.");
            setLoading(false);
            return;
        }

        try {
            const response = await api.applyUciToDevice(device.id, commandsArray);
            setCommandOutput(response.data.output);
        } catch (err) {
            console.error("Error applying commands:", err);
            const errMsg = err.response?.data?.error || err.response?.data?.details || err.message || 'Failed to apply commands';
            setError(errMsg);
            setCommandOutput(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal show={true} onHide={handleClose} backdrop="static" keyboard={false} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Execute Commands on {device?.name ?? 'Device'}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {error && <Alert variant="danger" onClose={() => setError(null)} dismissible>{error}</Alert>}
                <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                        <Form.Label>Commands</Form.Label>
                        <Form.Control
                            as="textarea"
                            rows={10}
                            placeholder="Example:\nuci show wireless\ndmesg | tail"
                            value={uciCommands}
                            onChange={(e) => setUciCommands(e.target.value)}
                            disabled={loading}
                        />
                        <Form.Text className="text-muted">
                            Enter commands to be executed sequentially. Lines starting with # are ignored.
                        </Form.Text>
                    </Form.Group>
                    
                    {commandOutput !== null && (
                        <Form.Group className="mb-3">
                             <Form.Label>Output</Form.Label>
                             <pre style={{ 
                                 maxHeight: '200px', 
                                 overflowY: 'auto', 
                                 backgroundColor: '#f8f9fa', 
                                 border: '1px solid #dee2e6', 
                                 padding: '10px' 
                             }}>
                                 {commandOutput}
                             </pre>
                         </Form.Group>
                    )}

                    <div className="d-flex justify-content-end">
                        <Button variant="secondary" onClick={handleClose} disabled={loading} className="me-2">
                            Close
                        </Button>
                        <Button variant="primary" type="submit" disabled={loading}>
                            {loading ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Executing...</> : 'Execute Commands'}
                        </Button>
                    </div>
                </Form>
            </Modal.Body>
        </Modal>
    );
}

export default ApplyUciModal; 