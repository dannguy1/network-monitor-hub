import React, { useState, useEffect, useCallback } from 'react';
import { Alert, Button, Spinner } from 'react-bootstrap'; // Added Button, Spinner
import api from '../services/api';
import DeviceForm from './DeviceForm'; // Import the form component
import ApplyUciModal from './ApplyUciModal'; // Import the modal

function DeviceList() {
    const [devices, setDevices] = useState([]);
    const [credentials, setCredentials] = useState([]); // Add state for credentials
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [editingDevice, setEditingDevice] = useState(null); // null for create, device object for edit
    const [actionError, setActionError] = useState(null); // For errors from actions
    const [actionMessage, setActionMessage] = useState(null); // For success messages
    const [selectedCredential, setSelectedCredential] = useState({}); // Store selected credential ID per device { deviceId: credId }
    const [verificationStatus, setVerificationStatus] = useState({}); // { credId: { status, message } }
    const [showUciModal, setShowUciModal] = useState(false); // State for UCI modal
    const [uciTargetDevice, setUciTargetDevice] = useState(null); // Device for UCI modal
    const [logConfigStatus, setLogConfigStatus] = useState({}); // { deviceId: { loading, enabled, target, error } }
    const [rebootingDevice, setRebootingDevice] = useState(null); // Track which device is rebooting
    const [refreshingDevice, setRefreshingDevice] = useState(null); // Track which device status is refreshing

    // Use useCallback to memoize fetch calls
    const fetchDevices = useCallback(() => {
        // Keep loading true until both devices and credentials are fetched
        setLoading(true);
        // Do not clear primary error on refetch, only action errors
        // setError(null);
        // Use Promise.all to fetch both devices and credentials concurrently
        Promise.all([
            api.getDevices(),
            api.getCredentials()
        ])
        .then(([devicesResponse, credentialsResponse]) => {
            setDevices(devicesResponse.data);
            setCredentials(credentialsResponse.data);
            setError(null); // Clear primary error only on success
            setLoading(false);
            // Fetch log config for each device *after* initial load
            devicesResponse.data.forEach(device => fetchLogConfig(device.id));
        })
        .catch(err => {
            console.error("Error fetching data:", err);
            setError(err.response?.data?.error || err.message || 'Failed to fetch data');
            setLoading(false);
        });
    }, []);

    useEffect(() => {
        fetchDevices();
    }, [fetchDevices]); // Fetch data on mount

    // Clear action messages/errors and verification statuses
    const clearActionFeedback = () => {
        setActionError(null);
        setActionMessage(null);
        setVerificationStatus({}); // Clear all verification statuses
    };

    const handleCreate = (formData) => {
        clearActionFeedback();
        api.createDevice(formData)
            .then(() => {
                setActionMessage(`Device '${formData.name}' created successfully.`);
                fetchDevices(); // Re-fetch the list
                setShowForm(false); // Hide form
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
                fetchDevices(); // Re-fetch the list
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
        if (window.confirm(`Are you sure you want to delete device '${device.name}'?`)) {
            api.deleteDevice(device.id)
                .then(() => {
                    setActionMessage(`Device '${device.name}' deleted successfully.`);
                    fetchDevices(); // Re-fetch the list
                })
                .catch(err => {
                    console.error("Error deleting device:", err);
                    setActionError(err.response?.data?.error || err.message || 'Failed to delete device');
                });
        }
    };

    // --- Association Handlers ---
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
                setSelectedCredential(prev => ({...prev, [deviceId]: ''})); // Clear selection for this device
                fetchDevices(); // Re-fetch to update device state
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
                    fetchDevices(); // Re-fetch to update device state
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
    };
    // --- End Association Handlers ---

    // --- Verification Handler ---
    const handleVerify = (credentialId) => {
        clearActionFeedback();
        setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'loading', message: 'Verifying...' } }));

        api.verifyCredential(credentialId)
            .then(response => {
                setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'success', message: response.data.message || 'Verification Successful' } }));
                // Optionally update device status if backend doesn't trigger a full refresh
                // fetchDevices(); // Or update device status directly in state if preferred
            })
            .catch(err => {
                 console.error("Error verifying credential:", err);
                 const errMsg = err.response?.data?.message || err.message || 'Verification Failed';
                 setVerificationStatus(prev => ({ ...prev, [credentialId]: { status: 'error', message: errMsg } }));
            });
    };
    // --- End Verification Handler ---

    // --- UCI Apply Handlers ---
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
            // Show success message briefly
            setActionMessage(`UCI commands applied successfully to ${uciTargetDevice.name}.`);
             // Automatically clear message after a few seconds
            setTimeout(() => setActionMessage(null), 5000);
            
            // Show full output in console for now
            console.log("Apply UCI STDOUT:", response.data.stdout);
            if (response.data.stderr) {
                console.warn("Apply UCI STDERR:", response.data.stderr);
                 setActionError(`Apply UCI completed with errors: ${response.data.stderr.substring(0, 100)}... (See console)`); // Show snippet
            }
            
            setShowUciModal(false);
            setUciTargetDevice(null);
        } catch (err) {
            console.error("Error applying UCI commands:", err);
            const errMsg = err.response?.data?.stderr || err.response?.data?.error || err.message || 'Failed to apply UCI commands';
            // Let the modal show the error directly for immediate feedback
            throw new Error(errMsg);
        }
    };

     const handleCancelUciModal = () => {
        setShowUciModal(false);
        setUciTargetDevice(null);
    };
    // --- End UCI Apply Handlers ---

    // --- Log Config Handlers ---
    const fetchLogConfig = useCallback(async (deviceId) => {
         // Only fetch if credential exists for the device
         const device = devices.find(d => d.id === deviceId);
         if (!device || !device.credential_id) {
             setLogConfigStatus(prev => ({ ...prev, [deviceId]: { loading: false, error: 'No credential associated' } }));
             return;
         }

        setLogConfigStatus(prev => ({ ...prev, [deviceId]: { loading: true } }));
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
            setLogConfigStatus(prev => ({ 
                ...prev, 
                [deviceId]: { 
                    loading: false, 
                    error: err.response?.data?.error || err.message || 'Failed to fetch status' 
                } 
            }));
        }
    }, [devices]); // Depend on devices list to find credential ID

    const handleToggleLogConfig = async (deviceId, currentState) => {
        clearActionFeedback();
        const newState = !currentState;
        setLogConfigStatus(prev => ({ ...prev, [deviceId]: { ...prev[deviceId], loading: true } })); // Show loading
        
        try {
            await api.setLogConfig(deviceId, newState);
            setActionMessage(`Remote logging ${newState ? 'enabled' : 'disabled'} successfully for device ID ${deviceId}.`);
            // Refetch status after successful toggle
            fetchLogConfig(deviceId);
        } catch (err) {
            console.error(`Error toggling log config for device ${deviceId}:`, err);
            setActionError(err.response?.data?.error || err.message || `Failed to ${newState ? 'enable' : 'disable'} logging`);
             // Reset loading state on error for the specific device
            setLogConfigStatus(prev => ({ ...prev, [deviceId]: { ...prev[deviceId], loading: false } }));
        }
    };
    // --- End Log Config Handlers ---

    // --- Reboot Handler ---
    const handleReboot = async (device) => {
        clearActionFeedback();
        if (!device.credential_id) {
            setActionError("Cannot reboot: Device has no associated credential.");
            return;
        }
        if (window.confirm(`Are you sure you want to reboot device '${device.name}'?`)) {
            setRebootingDevice(device.id); // Set loading state for this device
            setActionMessage(null); // Clear previous messages
            setActionError(null);
            try {
                const response = await api.rebootDevice(device.id);
                // Show success message (even if connection drops)
                setActionMessage(response.data.message || `Reboot command sent successfully to ${device.name}. Device may take a moment to restart.`);
                 // Optionally update device status to 'Rebooting' or 'Unknown'
                 // setDevices(prev => prev.map(d => d.id === device.id ? {...d, status: 'Rebooting'} : d));
            } catch (err) {
                console.error("Error rebooting device:", err);
                setActionError(err.response?.data?.message || err.response?.data?.error || err.message || 'Failed to send reboot command');
            } finally {
                setRebootingDevice(null); // Clear loading state regardless of outcome
            }
        }
    };
    // --- End Reboot Handler ---

    // --- Refresh Status Handler ---
    const handleRefreshStatus = async (deviceId) => {
        clearActionFeedback();
        setRefreshingDevice(deviceId); // Set loading state
        setActionMessage(null); // Clear previous messages
        setActionError(null);
        try {
            const response = await api.refreshDeviceStatus(deviceId);
            setActionMessage(response.data.message || `Status refresh attempt complete.`);
            
            // Update the device list state directly with the new status
            setDevices(prevDevices => 
                prevDevices.map(d => 
                    d.id === deviceId 
                        ? { ...d, status: response.data.device_status, last_seen: response.data.last_seen }
                        : d
                )
            );
            // Clear verification status for this credential if it existed, as we just refreshed
            const device = devices.find(d => d.id === deviceId);
            if (device && device.credential_id) {
                setVerificationStatus(prev => {
                    const { [device.credential_id]: _, ...rest } = prev; // Remove status for this credential
                    return rest;
                });
            }

        } catch (err) {
            console.error("Error refreshing device status:", err);
            const errMsg = err.response?.data?.message || err.response?.data?.error || err.message || 'Failed to refresh status';
            setActionError(errMsg);
             // Optionally update status to 'Unknown' or keep old one on error
             // setDevices(prevDevices => prevDevices.map(d => d.id === deviceId ? { ...d, status: 'Refresh Error' } : d));
        } finally {
            setRefreshingDevice(null); // Clear loading state
        }
    };
    // --- End Refresh Status Handler ---

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
        clearActionFeedback();
    };

    // Helper function to get credential name from ID
    const getCredentialName = (id) => {
        const cred = credentials.find(c => c.id === id);
        return cred ? cred.name : 'Unknown';
    };

    // Filter credentials to find those not associated with ANY device
    const availableCredentials = credentials.filter(cred => !cred.device_id);

    if (loading && !devices.length) return <p>Loading devices and credentials...</p>; // Show loading only initially
    // Show primary error prominently if loading failed
    if (error && !devices.length) return <Alert variant="danger">Error loading data: {error}</Alert>; 

    return (
        <div>
            <h2>Devices</h2>
            {/* Action feedback Alerts */} 
            {actionError && <Alert variant="danger" onClose={() => setActionError(null)} dismissible>{actionError}</Alert>}
            {actionMessage && <Alert variant="success" onClose={() => setActionMessage(null)} dismissible>{actionMessage}</Alert>}

            {!showForm && (
                 <button onClick={openCreateForm} className="btn btn-primary mb-3"> {/* Added Bootstrap class */} 
                     Add New Device
                 </button>
            )}

            {showForm && (
                <DeviceForm
                    initialDevice={editingDevice}
                    onSubmit={editingDevice ? handleUpdate : handleCreate}
                    onCancel={handleCancelForm}
                />
            )}
             {/* Display loading indicator if fetching updates */}
             {loading && devices.length > 0 && <p>Refreshing device list...</p>}

            {devices.length === 0 && !loading ? (
                <p>No devices found.</p>
            ) : (
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {devices.map(device => {
                        const currentVerification = verificationStatus[device.credential_id];
                        const currentLogStatus = logConfigStatus[device.id];
                        const isRebooting = rebootingDevice === device.id;
                        const isRefreshing = refreshingDevice === device.id;
                        return (
                        <li key={device.id} className="list-group-item mb-3 p-3"> {/* Bootstrap list styling */} 
                            <div className="d-flex justify-content-between align-items-center mb-2">
                                <h5 className="mb-0">{device.name} ({device.ip_address})</h5>
                                <div className="d-flex align-items-center">
                                    {/* Refresh Button */} 
                                     <Button 
                                         variant="link" 
                                         size="sm" 
                                         className="p-0 me-2" 
                                         onClick={() => handleRefreshStatus(device.id)}
                                         disabled={!device.credential_id || isRefreshing || isRebooting}
                                         title={!device.credential_id ? "Associate a credential to refresh status" : "Refresh Status"}
                                     >
                                         {isRefreshing 
                                             ? <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                                             : <i className="bi bi-arrow-clockwise"></i> /* Using Bootstrap Icons */
                                         }
                                     </Button>
                                    {/* Status Badge */}
                                    <span 
                                        className={`badge bg-${device.status === 'Online' || device.status === 'Verified' ? 'success' : (device.status === 'Unknown' || device.status === 'Rebooting' ? 'secondary' : 'danger')}`}
                                        title={`Status: ${device.status}`}
                                    >
                                        {device.status}
                                    </span>
                                </div>
                                <span className={`badge bg-${device.status === 'Online' || device.status === 'Verified' ? 'success' : 'secondary'}`}>{device.status}</span>
                            </div>
                            <p className="mb-1">{device.description || 'No description'}</p>
                            <small className="text-muted">Last Seen: {device.last_seen ? new Date(device.last_seen).toLocaleString() : 'Never'}</small>
                            
                            {/* --- Credential Association UI --- */}
                            <div className="mt-3 pt-3 border-top">
                                <h6>SSH Credential</h6>
                                {device.credential_id ? (
                                    <div className="d-flex align-items-center flex-wrap">
                                        <span>{getCredentialName(device.credential_id)}</span>
                                        <button
                                            onClick={() => handleVerify(device.credential_id)}
                                            className="btn btn-sm btn-outline-info ms-2" 
                                            disabled={currentVerification?.status === 'loading'}
                                        >
                                            {currentVerification?.status === 'loading' ? 'Verifying...' : 'Verify'}
                                        </button>
                                        <button
                                            onClick={() => handleDisassociate(device.id, getCredentialName(device.credential_id))}
                                            className="btn btn-sm btn-outline-warning ms-2"
                                        >
                                            Disassociate
                                        </button>
                                        {currentVerification && (
                                            <span className={`ms-2 badge bg-${currentVerification.status === 'success' ? 'success' : (currentVerification.status === 'error' ? 'danger' : 'secondary')}`}>
                                                {currentVerification.message}
                                            </span>
                                        )}
                                    </div>
                                ) : (
                                    <div className="input-group input-group-sm">
                                        <select
                                            className="form-select"
                                            value={selectedCredential[device.id] || ''}
                                            onChange={(e) => handleCredentialSelectChange(device.id, e)}
                                        >
                                            <option value="" disabled>Select Credential...</option>
                                            {availableCredentials.map(cred => (
                                                <option key={cred.id} value={cred.id}>
                                                    {cred.name} ({cred.ssh_username})
                                                </option>
                                            ))}
                                        </select>
                                        <button
                                             className="btn btn-outline-primary"
                                             onClick={() => handleAssociate(device.id)}
                                             disabled={!selectedCredential[device.id]}
                                        >
                                             Associate
                                         </button>
                                         {availableCredentials.length === 0 && <span className="ms-2 text-muted">(No available credentials)</span>}
                                    </div>
                                )}
                            </div>

                            {/* --- Remote Logging Control UI --- */} 
                             <div className="mt-3 pt-3 border-top">
                                <h6>Remote Logging (to this server)</h6>
                                {!device.credential_id ? (
                                    <small className="text-muted">Associate credential to manage logging.</small>
                                ) : currentLogStatus?.loading ? (
                                     <Spinner animation="border" size="sm" />
                                ) : currentLogStatus?.error ? (
                                    <><span className="text-danger">Error: {currentLogStatus.error}</span> <Button variant="link" size="sm" onClick={() => fetchLogConfig(device.id)}>Retry</Button></>
                                ) : currentLogStatus ? (
                                    <div>
                                        Status: <span className={`fw-bold ${currentLogStatus.enabled ? 'text-success' : 'text-secondary'}`}>{currentLogStatus.enabled ? 'Enabled' : 'Disabled'}</span>
                                        {currentLogStatus.enabled && <small className="text-muted ms-2">(Target: {currentLogStatus.target || 'N/A'})</small>}
                                        <Button 
                                            variant={currentLogStatus.enabled ? "outline-danger" : "outline-success"} 
                                            size="sm" 
                                            className="ms-3"
                                            onClick={() => handleToggleLogConfig(device.id, currentLogStatus.enabled)}
                                        >
                                            {currentLogStatus.enabled ? 'Disable Remote Logging' : 'Enable Remote Logging'}
                                        </Button>
                                    </div>
                                ) : (
                                     <Button variant="link" size="sm" onClick={() => fetchLogConfig(device.id)}>Check Status</Button>
                                )}
                            </div>
                            {/* --- End Remote Logging Control UI --- */} 

                            {/* Action Buttons */}
                            <div className="mt-3 pt-3 border-top d-flex flex-wrap gap-2"> {/* Use flexbox and gap */} 
                                 <Button onClick={() => openEditForm(device)} size="sm" variant="secondary" disabled={isRebooting}>Edit Device</Button>
                                 <Button
                                     onClick={() => openUciModal(device)}
                                     size="sm"
                                     variant="info"
                                     disabled={!device.credential_id || isRebooting}
                                     title={!device.credential_id ? "Associate a credential first" : "Apply UCI Commands"}
                                 >
                                     Apply UCI
                                 </Button>
                                 <Button 
                                     onClick={() => handleReboot(device)}
                                     size="sm"
                                     variant="warning"
                                     disabled={!device.credential_id || isRebooting}
                                     title={!device.credential_id ? "Associate a credential first" : "Reboot Device"}
                                 >
                                     {isRebooting ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Rebooting...</> : 'Reboot Device'}
                                 </Button>
                                  <Button onClick={() => handleDelete(device)} size="sm" variant="danger" disabled={isRebooting}>Delete Device</Button>
                            </div>
                        </li>
                    )})}
                </ul>
            )}

            {/* Render UCI Modal */} 
            {showUciModal && uciTargetDevice && (
                <ApplyUciModal
                    device={uciTargetDevice}
                    onSubmit={handleApplyUci}
                    onCancel={handleCancelUciModal}
                />
            )}
        </div>
    );
}

export default DeviceList; 