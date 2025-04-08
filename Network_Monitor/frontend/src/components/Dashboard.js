import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spinner, Alert } from 'react-bootstrap';
import { Wifi, FileEarmarkMedicalFill, ExclamationTriangleFill } from 'react-bootstrap-icons'; // Removed WifiOff
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

                {/* Placeholder for another card - e.g., System Status or Notifications */}
                 <Col md={6} lg={4}>
                    <Card bg="light">
                        <Card.Body>
                            <Card.Title><ExclamationTriangleFill className="me-2" /> System Status</Card.Title>
                             {/* These are just illustrative - a real endpoint would be needed */}
                            <p>Backend API: {error ? <span className="text-danger">Error</span> : <span className="text-success">Running</span>}</p>
                            <p>Syslog Listener: <span className="text-secondary">Unknown</span></p>
                            <p>AI Push Task: <span className="text-secondary">Unknown</span></p>
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