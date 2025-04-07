import React, { useState, useEffect } from 'react';
import api from '../services/api';

function LogList() {
    const [logs, setLogs] = useState([]);
    const [pagination, setPagination] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({}); // e.g., { device_id: 1, log_level: 'ERROR' }
    const [currentPage, setCurrentPage] = useState(1);

    useEffect(() => {
        setLoading(true);
        const params = { ...filters, page: currentPage, per_page: 20 }; // Add pagination
        
        api.getLogs(params)
            .then(response => {
                setLogs(response.data.logs);
                setPagination(response.data.pagination);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching logs:", err);
                setError(err.message || 'Failed to fetch logs');
                setLoading(false);
            });
    }, [filters, currentPage]); // Re-fetch when filters or page change

    // --- Basic Filter Handling (Example) ---
    const handleFilterChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({
             ...prev,
              [name]: value === '' ? undefined : value // Remove filter if empty
        }));
        setCurrentPage(1); // Reset to page 1 on filter change
    };

    // --- Pagination Handling --- 
    const handlePageChange = (newPage) => {
        if (newPage >= 1 && newPage <= pagination.total_pages) {
             setCurrentPage(newPage);
        }
    };

    return (
        <div>
            <h2>Logs</h2>
            
            {/* Basic Filter UI - Needs improvement */} 
            <div>
                <label>Device ID: </label>
                <input type="number" name="device_id" onChange={handleFilterChange} placeholder="Filter by Device ID"/>
                <label> Log Level: </label>
                <input type="text" name="log_level" onChange={handleFilterChange} placeholder="e.g., ERROR"/>
                 <label> Message Contains: </label>
                <input type="text" name="message_contains" onChange={handleFilterChange} placeholder="Search text..."/>
            </div>

            {loading && <p>Loading logs...</p>}
            {error && <p style={{ color: 'red' }}>Error: {error}</p>}
            
            {!loading && !error && (
                <>
                    {logs.length === 0 ? (
                        <p>No logs found matching criteria.</p>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr>
                                    <th style={{border: '1px solid #ddd', padding: '4px'}}>Timestamp</th>
                                    <th style={{border: '1px solid #ddd', padding: '4px'}}>Device IP</th>
                                    <th style={{border: '1px solid #ddd', padding: '4px'}}>Level</th>
                                    <th style={{border: '1px solid #ddd', padding: '4px'}}>Process</th>
                                    <th style={{border: '1px solid #ddd', padding: '4px'}}>Message</th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.map(log => (
                                    <tr key={log.id}>
                                        <td style={{border: '1px solid #ddd', padding: '4px', fontSize: '0.9em'}}>{new Date(log.timestamp).toLocaleString()}</td>
                                        <td style={{border: '1px solid #ddd', padding: '4px'}}>{log.device_ip}</td>
                                        <td style={{border: '1px solid #ddd', padding: '4px'}}>{log.log_level}</td>
                                        <td style={{border: '1px solid #ddd', padding: '4px'}}>{log.process_name}</td>
                                        <td style={{border: '1px solid #ddd', padding: '4px'}}>{log.message}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}

                    {/* Basic Pagination UI */} 
                    {pagination.total_pages > 1 && (
                        <div style={{ marginTop: '15px' }}>
                            <button onClick={() => handlePageChange(currentPage - 1)} disabled={!pagination.has_prev}>
                                Previous
                            </button>
                            <span style={{ margin: '0 10px' }}>
                                Page {pagination.page} of {pagination.total_pages} (Total: {pagination.total_items})
                            </span>
                            <button onClick={() => handlePageChange(currentPage + 1)} disabled={!pagination.has_next}>
                                Next
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default LogList; 