import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
// Import necessary React-Bootstrap components
import { Table, Spinner, Alert, Pagination, Card, Form, Row, Col, Button, Badge, Modal, Toast, ToastContainer } from 'react-bootstrap';
import { ArrowClockwise, Trash } from 'react-bootstrap-icons'; // Import refresh and trash icons
import { toast } from 'react-toastify'; // Import toast

// Define common log levels for filtering
const LOG_LEVELS = ['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY'];
const DEFAULT_LOGS_PER_PAGE = 50; // Set default page size

function LogList() {
    const [logs, setLogs] = useState([]);
    const [devices, setDevices] = useState([]); // Add state for devices (for filtering)
    const [pagination, setPagination] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // Store filter values separately
    const [filterDeviceId, setFilterDeviceId] = useState('');
    const [filterLogLevel, setFilterLogLevel] = useState('');
    const [filterMessage, setFilterMessage] = useState('');
    const [filterProcessName, setFilterProcessName] = useState('');
    const [filterStartDate, setFilterStartDate] = useState('');
    const [filterEndDate, setFilterEndDate] = useState('');
    // Active filters sent to API
    const [activeFilters, setActiveFilters] = useState({});
    const [currentPage, setCurrentPage] = useState(1);
    // Confirmation modal state
    const [showClearConfirm, setShowClearConfirm] = useState(false);
    const [clearingLogs, setClearingLogs] = useState(false);
    // Toast notification state
    const [showToast, setShowToast] = useState(false);
    const [toastMessage, setToastMessage] = useState('');
    const [toastVariant, setToastVariant] = useState('success');
    const [isPushing, setIsPushing] = useState(false); // State for button loading

    const fetchLogsAndDevices = useCallback(() => {
        setLoading(true);
        setError(null);

        const logParams = { ...activeFilters, page: currentPage, per_page: DEFAULT_LOGS_PER_PAGE };

        Promise.all([
            api.getLogs(logParams),
            api.getDevices() // Fetch devices for the filter dropdown
        ])
        .then(([logsResponse, devicesResponse]) => {
            setLogs(logsResponse.data.logs || []);
            setPagination(logsResponse.data.pagination || {});
            setDevices(devicesResponse.data || []);
            setError(null);
        })
        .catch(err => {
            console.error("Error fetching data:", err);
            setError(err.response?.data?.error || err.message || 'Failed to fetch data');
            setLogs([]); // Clear logs on error
            setPagination({});
        })
        .finally(() => {
            setLoading(false);
        });
    }, [activeFilters, currentPage]);

    useEffect(() => {
        fetchLogsAndDevices();
    }, [fetchLogsAndDevices]);

    // --- Filter Handling ---
    const handleApplyFilters = () => {
        const newFilters = {};
        if (filterDeviceId) newFilters.device_id = filterDeviceId;
        if (filterLogLevel) newFilters.log_level = filterLogLevel;
        if (filterMessage) newFilters.message_contains = filterMessage;
        if (filterProcessName) newFilters.process_name = filterProcessName;
        if (filterStartDate) newFilters.start_date = filterStartDate;
        if (filterEndDate) newFilters.end_date = filterEndDate;

        setActiveFilters(newFilters);
        setCurrentPage(1); // Reset to page 1 when filters change
    };

    const handleClearFilters = () => {
        setFilterDeviceId('');
        setFilterLogLevel('');
        setFilterMessage('');
        setFilterProcessName('');
        setFilterStartDate('');
        setFilterEndDate('');
        setActiveFilters({});
        setCurrentPage(1);
    };
    // --- End Filter Handling ---

    // --- Refresh Handling ---
    const handleRefresh = () => {
        setError(null); // Clear previous errors on refresh
        fetchLogsAndDevices(); // Re-fetch data with current page and filters
    };
    // --- End Refresh Handling ---

    // --- Clear Logs Handling ---
    const handleShowClearConfirm = () => setShowClearConfirm(true);
    const handleCloseClearConfirm = () => setShowClearConfirm(false);

    const handleClearLogs = async () => {
        setClearingLogs(true);
        setError(null);
        try {
            const response = await api.deleteAllLogs();
            setToastMessage(response.data.message || 'Logs cleared successfully!');
            setToastVariant('success');
            setShowToast(true);
            handleCloseClearConfirm();
            handleRefresh(); // Refresh the log list after clearing
        } catch (err) {
            console.error("Error clearing logs:", err);
            const errorMsg = err.response?.data?.error || err.message || 'Failed to clear logs';
            setError(errorMsg);
            setToastMessage(errorMsg);
            setToastVariant('danger');
            setShowToast(true);
            handleCloseClearConfirm(); // Still close modal on error
        } finally {
            setClearingLogs(false);
        }
    };
    // --- End Clear Logs Handling ---

    // --- Pagination Handling ---
    const handlePageChange = (newPage) => {
        if (newPage >= 1 && newPage <= pagination.total_pages && newPage !== currentPage) {
             setCurrentPage(newPage);
        }
    };

    const renderPaginationItems = () => {
        if (!pagination.total_pages || pagination.total_pages <= 1) return null;

        let items = [];
        const maxPagesToShow = 5; // Adjust as needed
        const startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
        const endPage = Math.min(pagination.total_pages, startPage + maxPagesToShow - 1);

        // Adjust startPage if endPage reaches the limit
        const adjustedStartPage = Math.max(1, endPage - maxPagesToShow + 1);

        items.push(
            <Pagination.First key="first" onClick={() => handlePageChange(1)} disabled={currentPage === 1} />,
            <Pagination.Prev key="prev" onClick={() => handlePageChange(currentPage - 1)} disabled={!pagination.has_prev} />
        );

        if (adjustedStartPage > 1) {
            items.push(<Pagination.Ellipsis key="start-ellipsis" disabled />);
        }

        for (let page = adjustedStartPage; page <= endPage; page++) {
            items.push(
                <Pagination.Item key={page} active={page === currentPage} onClick={() => handlePageChange(page)}>
                    {page}
                </Pagination.Item>
            );
        }

        if (endPage < pagination.total_pages) {
            items.push(<Pagination.Ellipsis key="end-ellipsis" disabled />);
        }

        items.push(
            <Pagination.Next key="next" onClick={() => handlePageChange(currentPage + 1)} disabled={!pagination.has_next} />,
            <Pagination.Last key="last" onClick={() => handlePageChange(pagination.total_pages)} disabled={currentPage === pagination.total_pages} />
        );

        return items;
    };
     // --- End Pagination Handling ---

    const getLogLevelVariant = (level) => {
        const upperLevel = level?.toUpperCase();
        switch (upperLevel) {
            case 'ERROR':
            case 'CRITICAL':
            case 'ALERT':
            case 'EMERGENCY':
                return 'danger';
            case 'WARNING':
                return 'warning';
            case 'NOTICE':
                return 'info';
            case 'DEBUG':
                return 'secondary';
            default: // INFO and others
                return 'success';
        }
    }

    // --- New Function to Handle AI Push --- //
    const handleTriggerAIPush = async () => {
        setIsPushing(true); // Set loading state for the button
        try {
            const response = await api.post('/dashboard/trigger-ai-push'); // Use correct endpoint
            if (response.data.success) {
                toast.success(response.data.message || 'AI Push triggered successfully!');
            } else {
                toast.error(response.data.message || 'Failed to trigger AI Push.');
            }
        } catch (error) {
            console.error("Error triggering AI Push:", error);
            const errorMsg = error.response?.data?.message || 'An error occurred while triggering the push.';
            toast.error(errorMsg);
        } finally {
            setIsPushing(false); // Reset loading state
        }
    };
    // ---------------------------------------

    return (
        <>
         <Card>
             <Card.Header>
                 <div className="d-flex justify-content-between align-items-center">
                     <h4 className="mb-0">System Logs</h4>
                     <div> {/* Group buttons */} 
                         <Button variant="outline-danger" size="sm" onClick={handleShowClearConfirm} disabled={loading || clearingLogs} className="me-2"> 
                             <Trash className="me-1" /> Clear All Logs
                         </Button>
                         <Button variant="outline-secondary" size="sm" onClick={handleRefresh} disabled={loading || clearingLogs}>
                             <ArrowClockwise className="me-1" /> Refresh
                         </Button>
                    </div>
                 </div>
             </Card.Header>
             <Card.Body>
                 {/* Filter Section */}
                 <Form className="mb-4 p-3 border rounded">
                     <Row className="g-3 align-items-end">
                         <Col md={3}>
                             <Form.Group controlId="filterDevice">
                                 <Form.Label>Device</Form.Label>
                                 <Form.Select value={filterDeviceId} onChange={(e) => setFilterDeviceId(e.target.value)}>
                                     <option value="">All Devices</option>
                                     {devices.map(device => (
                                         <option key={device.id} value={device.id}>
                                             {device.name} ({device.host})
                                         </option>
                                     ))}
                                 </Form.Select>
                             </Form.Group>
                         </Col>
                         <Col md={2}>
                            <Form.Group controlId="filterLevel">
                                <Form.Label>Log Level</Form.Label>
                                <Form.Select value={filterLogLevel} onChange={(e) => setFilterLogLevel(e.target.value)}>
                                     <option value="">All Levels</option>
                                     {LOG_LEVELS.map(level => (
                                         <option key={level} value={level}>{level}</option>
                                     ))}
                                 </Form.Select>
                            </Form.Group>
                         </Col>
                         <Col md={2}>
                             <Form.Group controlId="filterProcessName">
                                 <Form.Label>Process Name</Form.Label>
                                 <Form.Control
                                     type="text"
                                     placeholder="e.g., cron, kernel"
                                     value={filterProcessName}
                                     onChange={(e) => setFilterProcessName(e.target.value)}
                                 />
                             </Form.Group>
                         </Col>
                         <Col md={3}>
                             <Form.Group controlId="filterMessage">
                                 <Form.Label>Message Contains</Form.Label>
                                 <Form.Control
                                     type="text"
                                     placeholder="Search text..."
                                     value={filterMessage}
                                     onChange={(e) => setFilterMessage(e.target.value)}
                                 />
                             </Form.Group>
                         </Col>
                          {/* Placeholder for Date Filters */}
                          {/*
                           <Col md={2}>
                               <Form.Group controlId="filterStartDate">
                                   <Form.Label>Start Date</Form.Label>
                                   <Form.Control type="datetime-local" value={filterStartDate} onChange={(e) => setFilterStartDate(e.target.value)} />
                               </Form.Group>
                           </Col>
                           <Col md={2}>
                               <Form.Group controlId="filterEndDate">
                                   <Form.Label>End Date</Form.Label>
                                   <Form.Control type="datetime-local" value={filterEndDate} onChange={(e) => setFilterEndDate(e.target.value)} />
                               </Form.Group>
                           </Col>
                          */}
                         <Col md={3} className="d-flex justify-content-end">
                             <Button variant="primary" onClick={handleApplyFilters} className="me-2">Apply Filters</Button>
                             <Button variant="secondary" onClick={handleClearFilters}>Clear</Button>
                             <Button
                                variant="info"
                                onClick={handleTriggerAIPush}
                                className="ms-2"
                                disabled={isPushing || loading}
                             >
                                {isPushing ? <><Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> Pushing...</> : 'Push Logs to AI'}
                             </Button>
                         </Col>
                     </Row>
                 </Form>

                 {/* Loading and Error Display */} 
                 {loading && ( 
                     <div className="text-center my-3">
                         <Spinner animation="border" role="status">
                             <span className="visually-hidden">Loading Logs...</span>
                         </Spinner>
                    </div>
                 )}
                {error && !clearingLogs && <Alert variant="danger">Error: {error}</Alert>}

                 {/* Log Table */} 
                 {!loading && !error && (
                    <>
                    <Table striped bordered hover responsive size="sm" className="mt-3 align-middle">
                        <thead>
                            <tr>
                                <th style={{ width: '15%' }}>Timestamp</th>
                                <th style={{ width: '15%' }}>Device</th>
                                <th style={{ width: '8%' }}>Level</th>
                                <th style={{ width: '12%' }}>Process</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="text-center">No logs found matching criteria.</td>
                                </tr>
                            ) : (
                                logs.map(log => (
                                    <tr key={log.id}>
                                        <td>{new Date(log.timestamp).toLocaleString()}</td>
                                        <td>{log.device_name || log.device_ip || 'N/A'}</td>
                                        <td>
                                             <Badge bg={getLogLevelVariant(log.log_level)} text={getLogLevelVariant(log.log_level) === 'warning' ? 'dark' : 'white'}>
                                                 {log.log_level || '-'}
                                             </Badge>
                                         </td>
                                         <td>{log.process_name || '-'}</td>
                                         <td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{log.message}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </Table>

                     {/* Pagination Controls */}
                    {pagination.total_pages > 0 && (
                        <div className="d-flex justify-content-between align-items-center mt-3">
                            <small className="text-muted">
                                Showing {logs.length} of {pagination.total_items} logs
                            </small>
                            <Pagination size="sm">
                                 {renderPaginationItems()}
                             </Pagination>
                         </div>
                     )}
                     </>
                 )}
             </Card.Body>
         </Card>

         {/* Confirmation Modal */}
         <Modal show={showClearConfirm} onHide={handleCloseClearConfirm} centered>
             <Modal.Header closeButton>
                 <Modal.Title>Confirm Clear Logs</Modal.Title>
             </Modal.Header>
             <Modal.Body>
                 Are you sure you want to permanently delete all log entries? This action cannot be undone.
             </Modal.Body>
             <Modal.Footer>
                 <Button variant="secondary" onClick={handleCloseClearConfirm} disabled={clearingLogs}>
                     Cancel
                 </Button>
                 <Button variant="danger" onClick={handleClearLogs} disabled={clearingLogs}>
                     {clearingLogs ? <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> : 'Clear All Logs'}
                 </Button>
             </Modal.Footer>
         </Modal>

         {/* Toast Notifications */}
         <ToastContainer position="top-end" className="p-3" style={{ zIndex: 1056 }}>
            <Toast onClose={() => setShowToast(false)} show={showToast} delay={5000} autohide bg={toastVariant}>
                <Toast.Header closeButton={true}>
                     <strong className="me-auto">Log Action</strong>
                 </Toast.Header>
                 <Toast.Body className={toastVariant === 'danger' ? 'text-white' : ''}>{toastMessage}</Toast.Body>
             </Toast>
         </ToastContainer>
        </>
    );
}

export default LogList; 