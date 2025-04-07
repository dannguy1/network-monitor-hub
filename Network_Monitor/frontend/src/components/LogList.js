import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
// Import necessary React-Bootstrap components
import { Table, Spinner, Alert, Pagination, Card, Form, Row, Col, Button, Badge } from 'react-bootstrap';

// Define common log levels for filtering
const LOG_LEVELS = ['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY'];

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
    const [filterStartDate, setFilterStartDate] = useState('');
    const [filterEndDate, setFilterEndDate] = useState('');
    // Active filters sent to API
    const [activeFilters, setActiveFilters] = useState({});
    const [currentPage, setCurrentPage] = useState(1);

    const fetchLogsAndDevices = useCallback(() => {
        setLoading(true);
        setError(null);

        const logParams = { ...activeFilters, page: currentPage, per_page: 30 }; // Increase per_page

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
        if (filterStartDate) newFilters.start_date = filterStartDate;
        if (filterEndDate) newFilters.end_date = filterEndDate;

        setActiveFilters(newFilters);
        setCurrentPage(1); // Reset to page 1 when filters change
    };

    const handleClearFilters = () => {
        setFilterDeviceId('');
        setFilterLogLevel('');
        setFilterMessage('');
        setFilterStartDate('');
        setFilterEndDate('');
        setActiveFilters({});
        setCurrentPage(1);
    };
    // --- End Filter Handling ---

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

    return (
         <Card>
             <Card.Header>
                 <h4 className="mb-0">System Logs</h4>
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
                         <Col md={4}>
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
                {error && <Alert variant="danger">Error loading logs: {error}</Alert>}

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
    );
}

export default LogList; 