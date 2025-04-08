import React, { useState, useEffect, useCallback } from 'react';
import { Alert, Button, Spinner, Table, Card, Badge, ButtonGroup, Form } from 'react-bootstrap';
import api from '../services/api';
import DeviceForm from './DeviceForm';
import ApplyUciModal from './ApplyUciModal';
import { PencilSquare, Trash, Key, CheckCircle, XCircle, ArrowRepeat, GearFill, Power, CloudArrowUpFill, CloudSlashFill } from 'react-bootstrap-icons';

function DeviceList() {
    const [devices, setDevices] = useState([]);
    const [credentials, setCredentials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingDevice, setEditingDevice] = useState(null);
    const [actionError, setActionError] = useState(null);
    const [actionMessage, setActionMessage] = useState(null);
    const [selectedCredential, setSelectedCredential] = useState({});
    const [verificationStatus, setVerificationStatus] = useState({});
    const [showUciModal, setShowUciModal] = useState(false);
    const [uciTargetDevice, setUciTargetDevice] = useState(null);
    const [logConfigStatus, setLogConfigStatus] = useState({});
    const [rebootingDevice, setRebootingDevice] = useState(null);
    const [refreshingDevice, setRefreshingDevice] = useState(null);

    // --- Define fetchLogConfig first --- //
    const fetchLogConfig = useCallback(async (deviceId, currentDevices) => {
        const device = currentDevices.find(d => d.id === deviceId);
         if (!device || !device.credential_id) {
             setLogConfigStatus(prev => ({ ...prev, [deviceId]: { loading: false, error: 'No credential' } }));
             return;
         }

        setLogConfigStatus(prev => ({ ...prev, [deviceId]: { ...prev[deviceId], loading: true, error: null } }));
        try {
            const response = await api.getLogConfig(deviceId);
            setLogConfigStatus(prev => ({
                ...prev,
                [deviceId]: {
                    loading: false,
                    enabled: response.data.remote_logging_enabled,
                    target: response.data.remote_log_target,
                    error: null
                }
            }));
        } catch (err) {
            console.error(`Error fetching log config for device ${deviceId}:`, err);
             const errMsg = err.response?.data?.error || err.message || 'Failed to fetch status';
             setLogConfigStatus(prev => ({
                ...prev,
                [deviceId]: {
                     ...(prev[deviceId] || {}),
                    loading: false,
                    error: errMsg
                }
            }));
        }
    }, []); // Dependency array for fetchLogConfig (currently empty, adjust if needed)
    // --- End fetchLogConfig definition ---

    const fetchDevices = useCallback((clearActionFeedback = true) => {
        if (clearActionFeedback) {
            setActionError(null);
            setActionMessage(null);
        }
        setLoading(true);

        Promise.all([
            api.getDevices(),
            api.getCredentials()
        ])
        .then(([devicesResponse, credentialsResponse]) => {
            const fetchedDevices = devicesResponse.data || [];
            setDevices(fetchedDevices);
            setCredentials(credentialsResponse.data || []);
            setError(null);

            const initialLogStatus = {};
            fetchedDevices.forEach(device => {
                initialLogStatus[device.id] = { loading: false, enabled: undefined, target: undefined, error: null };
                if (device.credential_id) {
                   fetchLogConfig(device.id, fetchedDevices);
                } else {
                   initialLogStatus[device.id] = { loading: false, error: 'No credential associated' };
                }
                if (!selectedCredential[device.id]) {
                    setSelectedCredential(prev => ({ ...prev, [device.id]: '' }));
                }
            });
            setLogConfigStatus(initialLogStatus);

        })
        .catch(err => {
            console.error("Error fetching data:", err);
            setError(err.response?.data?.error || err.message || 'Failed to fetch data');
        })
        .finally(() => {
            setLoading(false);
        });
    }, [fetchLogConfig]);

    useEffect(() => {
        fetchDevices(true);
    }, [fetchDevices]);

    const clearActionFeedback = () => {
        setActionError(null);
        setActionMessage(null);
        setVerificationStatus({});
    };

    const handleCreate = (formData) => {
        clearActionFeedback();
        api.createDevice(formData)
            .then(() => {
                setActionMessage(`Device '${formData.name}' created successfully.`);
                fetchDevices(false);
                setShowForm(false);
            })
            .catch(err => {
                console.error("Error creating device:", err);
                setActionError(err.response?.data?.error || err.message || 'Failed to create device');
            });
    };

    const handleUpdate = (formData) => {
        clearActionFeedback();
        if (!editingDevice) return;
        api.updateDevice(editingDevice.id, formData)
            .then(() => {
                setActionMessage(`Device '${formData.name}' updated successfully.`);
                fetchDevices(false);
                setShowForm(false);
                setEditingDevice(null);
            })
            .catch(err => {
                console.error("Error updating device:", err);
                setActionError(err.response?.data?.error || err.message || 'Failed to update device');
            });
    };

    const handleDelete = (device) => {
        clearActionFeedback();
        if (window.confirm(`Are you sure you want to delete device '${device.name}'? This cannot be undone.`)) {
            api.deleteDevice(device.id)
                .then(() => {
                    setActionMessage(`Device '${device.name}' deleted successfully.`);
                    fetchDevices(false);
                })
                .catch(err => {
                    console.error("Error deleting device:", err);
                    setActionError(err.response?.data?.error || err.message || 'Failed to delete device');
                });
        }
    };

    const handleAssociate = (deviceId) => {
        clearActionFeedback();
        const credId = selectedCredential[deviceId];
        if (!credId) {
            setActionError("Please select a credential to associate.");
            return;
        }
        api.associateCredential(deviceId, credId)
            .then(response => {
                setActionMessage(response.data.message || `Credential associated successfully.`);
                setSelectedCredential(prev => ({...prev, [deviceId]: ''}));
                fetchDevices();
            })
            .catch(err => {
                 console.error("Error associating credential:", err);
                 setActionError(err.response?.data?.error || err.message || 'Failed to associate credential');
            });
    };

    const handleDisassociate = (deviceId, credentialName) => {
        clearActionFeedback();
        if (window.confirm(`Disassociate credential '${credentialName}' from this device?`)) {
            api.disassociateCredential(deviceId)
                .then(response => {
                    setActionMessage(response.data.message || `Credential disassociated successfully.`);
                    fetchDevices();
                })
                .catch(err => {
                    console.error("Error disassociating credential:", err);
                    setActionError(err.response?.data?.error || err.message || 'Failed to disassociate credential');
                });
        }
    };

    const handleCredentialSelectChange = (deviceId, event) => {
        setSelectedCredential(prev => ({
            ...prev,
            [deviceId]: event.target.value
        }));
        const device = devices.find(d => d.id === deviceId);
        if (device && device.credential_id) {
            setVerificationStatus(prev => {
                 const newStatus = { ...prev };
                 delete newStatus[device.credential_id];
                 return newStatus;
             });
        }
    };

    const handleVerify = (credentialId) => {
        clearActionFeedback();
         setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'loading', message: 'Verifying...' } }));

        api.verifyCredential(credentialId)
            .then(response => {
                setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'success', message: response.data.message || 'Verification Successful' } }));
            })
            .catch(err => {
                 console.error("Error verifying credential:", err);
                 const errMsg = err.response?.data?.message || err.response?.data?.error || err.message || 'Verification Failed';
                 setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'error', message: errMsg } }));
            });
    };

    const openUciModal = (device) => {
        if (!device.credential_id) {
            clearActionFeedback();
            setActionError("Cannot apply UCI: Device has no associated credential.");
            return;
        }
        clearActionFeedback();
        setUciTargetDevice(device);
        setShowUciModal(true);
    };

    const handleApplyUci = async (uciCommands) => {
        clearActionFeedback();
        if (!uciTargetDevice) return;

        try {
            const response = await api.applyUciToDevice(uciTargetDevice.id, uciCommands);
            setActionMessage(`UCI commands applied successfully to ${uciTargetDevice.name}.`);
            setTimeout(() => setActionMessage(null), 5000);
            
            console.log("Apply UCI STDOUT:", response.data.stdout);
            if (response.data.stderr) {
                console.warn("Apply UCI STDERR:", response.data.stderr);
                 setActionError(`Apply UCI completed with errors: ${response.data.stderr.substring(0, 100)}... (See console)`);
            }
            
            setShowUciModal(false);
            setUciTargetDevice(null);
        } catch (err) {
            console.error("Error applying UCI commands:", err);
            const errMsg = err.response?.data?.stderr || err.response?.data?.error || err.message || 'Failed to apply UCI commands';
            throw new Error(errMsg);
        }
    };

     const handleCancelUciModal = () => {
        setShowUciModal(false);
        setUciTargetDevice(null);
    };

    const handleToggleLogConfig = async (deviceId, currentState) => {
        clearActionFeedback();
        const newState = !currentState;
        const originalStatus = logConfigStatus[deviceId];
        setLogConfigStatus(prev => ({ ...prev, [deviceId]: { ...prev[deviceId], loading: true, error: null } }));

        try {
            const response = await api.toggleLogConfig(deviceId, newState);
            setLogConfigStatus(prev => ({
                ...prev,
                [deviceId]: {
                    loading: false,
                    enabled: response.data.remote_logging_enabled,
                    target: response.data.remote_log_target,
                    error: null
                }
            }));
             setActionMessage(`Remote logging ${newState ? 'enabled' : 'disabled'} for device.`);
             setTimeout(() => setActionMessage(null), 3000);
        } catch (err) {
            console.error(`Error toggling log config for device ${deviceId}:`, err);
            const errMsg = err.response?.data?.error || err.message || 'Failed to toggle logging';
             setActionError(errMsg);
             setLogConfigStatus(prev => ({ ...prev, [deviceId]: { ...originalStatus, loading: false, error: errMsg } }));
        }
    };

    const handleReboot = async (device) => {
        clearActionFeedback();
        if (!device.credential_id) {
            setActionError("Cannot reboot: Device has no associated credential.");
            return;
        }
        if (window.confirm(`Are you sure you want to reboot device '${device.name}'?`)) {
            setRebootingDevice(device.id);
            setActionMessage(null);
            setActionError(null);
            try {
                const response = await api.rebootDevice(device.id);
                setActionMessage(response.data.message || `Reboot command sent successfully to ${device.name}. Device may take a moment to restart.`);
            } catch (err) {
                console.error("Error rebooting device:", err);
                setActionError(err.response?.data?.message || err.response?.data?.error || err.message || 'Failed to send reboot command');
            } finally {
                setRebootingDevice(null);
            }
        }
    };

    const handleRefreshStatus = async (deviceId) => {
        clearActionFeedback();
        setRefreshingDevice(deviceId);
        const device = devices.find(d => d.id === deviceId);
        if (device && device.credential_id) {
            await fetchLogConfig(deviceId, devices);
        } else {
            setLogConfigStatus(prev => ({ ...prev, [deviceId]: { loading: false, error: 'No credential' } }));
        }
        setRefreshingDevice(null);
         setActionMessage("Device status refreshed.");
         setTimeout(() => setActionMessage(null), 2000);
    };

    const openEditForm = (device) => {
        clearActionFeedback();
        setEditingDevice(device);
        setShowForm(true);
    };

    const openCreateForm = () => {
        clearActionFeedback();
        setEditingDevice(null);
        setShowForm(true);
    };

    const handleCancelForm = () => {
        setShowForm(false);
        setEditingDevice(null);
    };

    const getCredentialName = (id) => {
        const cred = credentials.find(c => c.id === id);
        return cred ? cred.name : 'N/A';
    };

    const renderVerificationStatus = (credId) => {
        const status = verificationStatus[credId];
        if (!status) return null;

        if (status.status === 'loading') {
            return <Spinner animation="border" size="sm" className="ms-2" />;
        } else if (status.status === 'success') {
            return <Badge bg="success" className="ms-2" title={status.message}><CheckCircle /> Success</Badge>;
        } else if (status.status === 'error') {
            return <Badge bg="danger" className="ms-2" title={status.message}><XCircle /> Failed</Badge>;
        }
        return null;
    };

    const renderLogConfigStatus = (deviceId) => {
        const status = logConfigStatus[deviceId];
        if (!status) return <Spinner animation="border" size="sm" />;
        if (status.loading) return <Spinner animation="border" size="sm" />;
        if (status.error) return <Badge bg="warning" text="dark" title={status.error}>Error</Badge>;

        return (
            <>
                {status.enabled ? (
                    <Badge bg="success" title={`Target: ${status.target || 'N/A'}`}>Enabled</Badge>
                ) : (
                    <Badge bg="secondary">Disabled</Badge>
                )}
                <Button
                    variant="outline-secondary"
                    size="sm"
                    className="ms-2"
                    onClick={() => handleToggleLogConfig(deviceId, status.enabled)}
                    disabled={status.loading || !!status.error}
                    title={status.enabled ? 'Disable Remote Logging' : 'Enable Remote Logging'}
                >
                    {status.enabled ? <CloudSlashFill /> : <CloudArrowUpFill />}
                </Button>
            </>
        );
    };

    if (loading && devices.length === 0) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '200px' }}>
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading Devices...</span>
                </Spinner>
            </div>
        );
    }

    if (error && devices.length === 0) {
        return <Alert variant="danger">Error loading devices: {error}</Alert>;
    }

    return (
         <Card>
             <Card.Header className="d-flex justify-content-between align-items-center">
                 <h4 className="mb-0">Monitored Devices</h4>
                 <Button variant="primary" onClick={openCreateForm}>
                     Add New Device
                 </Button>
             </Card.Header>
             <Card.Body>
                 {actionError && <Alert variant="danger" onClose={() => setActionError(null)} dismissible>{actionError}</Alert>}
                 {actionMessage && <Alert variant="success" onClose={() => setActionMessage(null)} dismissible>{actionMessage}</Alert>}

                 {showForm && (
                     <Card className="mb-4">
                         <Card.Body>
                             <DeviceForm
                                 device={editingDevice}
                                 onSubmit={editingDevice ? handleUpdate : handleCreate}
                                 onCancel={handleCancelForm}
                             />
                         </Card.Body>
                     </Card>
                 )}

                 {loading && devices.length > 0 && <Spinner animation="border" size="sm" className="me-2" />}
                 {error && <Alert variant="warning">Could not refresh device list: {error}</Alert>}

                 <Table striped bordered hover responsive className="mt-3 align-middle">
                     <thead>
                         <tr>
                             <th>Name</th>
                             <th>Hostname / IP</th>
                             <th>Status</th>
                             <th>Remote Logging</th>
                             <th>Credential</th>
                             <th>Actions</th>
                         </tr>
                     </thead>
                     <tbody>
                         {devices.length === 0 && !loading ? (
                            <tr>
                                <td colSpan="6" className="text-center">No devices configured yet.</td>
                            </tr>
                         ) : (
                             devices.map(device => (
                                 <tr key={device.id}>
                                     <td>{device.name}</td>
                                     <td>{device.host}</td>
                                     <td>
                                         {refreshingDevice === device.id ? (
                                              <Spinner animation="border" size="sm" />
                                         ) : (
                                             <Badge bg={device.credential_id ? "success" : "secondary"}>
                                                  {device.credential_id ? "Managed" : "Unmanaged"}
                                             </Badge>
                                         )}
                                         <Button
                                             variant="link"
                                             size="sm"
                                             onClick={() => handleRefreshStatus(device.id)}
                                             disabled={refreshingDevice === device.id}
                                             title="Refresh Status"
                                             className="p-0 ms-1 align-baseline"
                                          >
                                              <ArrowRepeat />
                                          </Button>
                                     </td>
                                     <td>{renderLogConfigStatus(device.id)}</td>
                                     <td>
                                         {device.credential_id ? (
                                             <div className="d-flex align-items-center">
                                                 <span>{getCredentialName(device.credential_id)}</span>
                                                 <Button variant="link" size="sm" onClick={() => handleVerify(device.credential_id)} className="p-0 ms-1" title="Verify SSH Connection">
                                                     <Key />
                                                 </Button>
                                                 {renderVerificationStatus(device.credential_id)}
                                                 <Button variant="outline-danger" size="sm" className="ms-2" onClick={() => handleDisassociate(device.id, getCredentialName(device.credential_id))} title="Disassociate Credential">
                                                     <XCircle />
                                                 </Button>
                                             </div>
                                         ) : (
                                             <div className="d-flex align-items-center">
                                                 <Form.Select
                                                     size="sm"
                                                     value={selectedCredential[device.id] || ''}
                                                     onChange={(e) => handleCredentialSelectChange(device.id, e)}
                                                     className="me-2"
                                                     style={{ maxWidth: '150px' }}
                                                 >
                                                     <option value="">Select Credential...</option>
                                                     {credentials.map(cred => (
                                                         <option key={cred.id} value={cred.id}>{cred.name}</option>
                                                     ))}
                                                 </Form.Select>
                                                 <Button
                                                      variant="outline-primary"
                                                      size="sm"
                                                      onClick={() => handleAssociate(device.id)}
                                                      disabled={!selectedCredential[device.id]}
                                                  >
                                                      Associate
                                                  </Button>
                                             </div>
                                         )}
                                     </td>
                                     <td>
                                         <ButtonGroup size="sm">
                                             <Button variant="outline-secondary" onClick={() => openEditForm(device)} title="Edit Device">
                                                 <PencilSquare />
                                             </Button>
                                             <Button
                                                  variant="outline-info"
                                                  onClick={() => openUciModal(device)}
                                                  disabled={!device.credential_id || logConfigStatus[device.id]?.loading || refreshingDevice === device.id}
                                                  title="Apply UCI Config"
                                              >
                                                 <GearFill />
                                             </Button>
                                             <Button
                                                 variant="outline-warning"
                                                 onClick={() => handleReboot(device)}
                                                  disabled={!device.credential_id || rebootingDevice === device.id || logConfigStatus[device.id]?.loading || refreshingDevice === device.id}
                                                  title="Reboot Device"
                                              >
                                                 {rebootingDevice === device.id ? <Spinner as="span" animation="border" size="sm" /> : <Power />}
                                             </Button>
                                             <Button variant="outline-danger" onClick={() => handleDelete(device)} title="Delete Device">
                                                 <Trash />
                                             </Button>
                                         </ButtonGroup>
                                     </td>
                                 </tr>
                             ))
                         )}
                     </tbody>
                 </Table>

                 {uciTargetDevice && showUciModal && (
                    <ApplyUciModal
                        show={showUciModal}
                        handleClose={handleCancelUciModal}
                        handleApply={handleApplyUci}
                        deviceName={uciTargetDevice.name}
                        deviceHost={uciTargetDevice.host}
                    />
                 )}

             </Card.Body>
         </Card>
    );
}

export default DeviceList; 