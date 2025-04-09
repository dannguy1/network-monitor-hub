import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spinner, Alert, Badge } from 'react-bootstrap';
import { Wifi, FileEarmarkMedicalFill, ExclamationTriangleFill, Server, CloudArrowUpFill } from 'react-bootstrap-icons'; // Removed WifiOff
import api from '../services/api'; // We will need this later

function Dashboard() {
    const [summaryData, setSummaryData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        setLoading(true);
        setError(null);

        // Fetch actual summary data from the new API endpoint
        api.getDashboardSummary()
            .then(response => {
                setSummaryData(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching dashboard summary:", err);
                setError(err.response?.data?.error || err.message || 'Failed to load dashboard data');
                setLoading(false);
            });

    }, []); // Empty dependency array means this runs once on mount

    const getStatusBadge = (status) => {
        if (!status) return <Badge bg="secondary">Unknown</Badge>;
        const lowerStatus = status.toLowerCase();
        if (lowerStatus.includes('running') || lowerStatus.includes('scheduled')) {
            return <Badge bg="success">{status}</Badge>;
        } else if (lowerStatus.includes('stopped') || lowerStatus.includes('disabled') || lowerStatus.includes('inactive')) {
            return <Badge bg="warning" text="dark">{status}</Badge>;
        } else if (lowerStatus.includes('error')) {
            return <Badge bg="danger">{status}</Badge>;
        } else {
            return <Badge bg="secondary">{status}</Badge>; // Default for Unknown, Check Error etc.
        }
    };

    if (loading) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '200px' }}>
                <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading Dashboard...</span>
                </Spinner>
            </div>
        );
    }

    if (error) {
        return <Alert variant="danger">Error loading dashboard: {error}</Alert>;
    }

    return (
        <div>
            <h2>Dashboard Overview</h2>
            <Row className="mt-4 g-4"> {/* g-4 adds gutter spacing */}
                {/* Devices Summary Card */}
                <Col md={6} lg={4}>
                    <Card>
                        <Card.Body>
                            <Card.Title><Wifi className="me-2" /> Devices</Card.Title>
                            <h3 className="display-6">{summaryData?.total_devices ?? <Spinner size="sm"/>}</h3>
                            <p className="mb-1">Managed: {summaryData?.managed_devices ?? '-'}</p>
                            <p className="mb-0">Unmanaged: {summaryData?.unmanaged_devices ?? '-'}</p>
                            {/* <p className="mb-1">Online: {summaryData?.online_devices ?? '-'}</p>
                            <p className="mb-0">Offline: {summaryData?.offline_devices ?? '-'}</p> */}
                        </Card.Body>
                    </Card>
                </Col>

                 {/* Logs Summary Card */}
                 <Col md={6} lg={4}>
                     <Card>
                         <Card.Body>
                             <Card.Title><FileEarmarkMedicalFill className="me-2"/> Logs Today</Card.Title>
                              <h3 className="display-6 text-warning">{summaryData?.warning_logs_today ?? <Spinner size="sm"/>}</h3>
                              <p className="mb-1">Warnings</p>
                             <h3 className="display-6 text-danger">{summaryData?.critical_logs_today ?? <Spinner size="sm"/>}</h3>
                             <p className="mb-0">Critical/Errors</p>
                         </Card.Body>
                     </Card>
                 </Col>

                {/* System Status Card */}
                 <Col md={6} lg={4}>
                    <Card bg="light">
                        <Card.Body>
                            <Card.Title><ExclamationTriangleFill className="me-2" /> System Status</Card.Title>
                            {/* Add simple API status indicator */}
                            <Row className="mb-2">
                                <Col xs={8}><span className="text-primary">&#9889;</span> Backend API:</Col> 
                                <Col xs={4} className="text-end">
                                    {/* If we have data, API is responding */}
                                    {summaryData ? <Badge bg="success">Running</Badge> : <Badge bg="danger">Error</Badge>}
                                </Col>
                            </Row>
                            <Row className="mb-2">
                                <Col xs={8}><Server className="me-1" /> Syslog Listener:</Col>
                                <Col xs={4} className="text-end">{getStatusBadge(summaryData?.syslog_listener_status)}</Col>
                            </Row>
                            <Row>
                                <Col xs={8}><CloudArrowUpFill className="me-1" /> AI Pusher:</Col>
                                <Col xs={4} className="text-end">{getStatusBadge(summaryData?.ai_pusher_status)}</Col>
                            </Row>
                            {/* Add more relevant status info here */}
                        </Card.Body>
                    </Card>
                </Col>

            </Row>
            {/* Add more rows or components like recent logs table, device status list etc. later */}
        </div>
    );
}

export default Dashboard; 