import axios from 'axios';
import Cookies from 'js-cookie';

// Get the base URL from environment variables or default
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api/v1'; // Default to relative path for proxy

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, // Send cookies with requests
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add a request interceptor to include the CSRF token if available
apiClient.interceptors.request.use(config => {
    const csrfToken = Cookies.get('csrf_access_token'); // Default cookie name for Flask-Login CSRF
    if (csrfToken) {
        config.headers['X-CSRF-TOKEN'] = csrfToken;
    }
    return config;
});

// Handle unauthorized errors globally (e.g., redirect to login)
apiClient.interceptors.response.use(
    response => response,
    error => {
        if (error.response && error.response.status === 401) {
            // Clear potentially stale auth state (implementation depends on your AuthContext)
            // For example: authContext.logout();
            // Redirect to login page
            if (window.location.pathname !== '/login') { // Avoid redirect loop
                 window.location.href = '/login'; // Simple redirect
            }
        }
        return Promise.reject(error);
    }
);

// --- Authentication --- //
const login = (data) => apiClient.post('/auth/login', data);
const logout = () => apiClient.post('/auth/logout');
const checkAuthStatus = () => apiClient.get('/auth/status'); // Renamed for clarity?
const createUser = (username, password) => apiClient.post('/auth/create-user', { username, password }); // Admin only usually

// --- Devices --- //
const getDevices = () => apiClient.get('/devices');
const getDevice = (id) => apiClient.get(`/devices/${id}`);
const createDevice = (data) => apiClient.post('/devices', data);
const updateDevice = (id, data) => apiClient.put(`/devices/${id}`, data);
const deleteDevice = (id) => apiClient.delete(`/devices/${id}`);
const associateCredential = (deviceId, credentialId) => apiClient.post(`/devices/${deviceId}/associate`, { credential_id: credentialId });
const disassociateCredential = (deviceId) => apiClient.post(`/devices/${deviceId}/disassociate`);
const rebootDevice = (deviceId) => apiClient.post(`/devices/${deviceId}/reboot`); // New
const refreshDeviceStatus = (deviceId) => apiClient.get(`/devices/${deviceId}/status`); // New
const getLogConfig = (deviceId) => apiClient.get(`/devices/${deviceId}/log-config`);
const toggleLogConfig = (deviceId, enable) => apiClient.post(`/devices/${deviceId}/log-config`, { enable });

// --- Credentials --- //
const getCredentials = () => apiClient.get('/credentials');
const getCredential = (id) => apiClient.get(`/credentials/${id}`);
const createCredential = (data) => apiClient.post('/credentials', data);
const updateCredential = (id, data) => apiClient.put(`/credentials/${id}`, data);
const deleteCredential = (id) => apiClient.delete(`/credentials/${id}`);
const verifyCredential = (id) => apiClient.post(`/credentials/${id}/verify`);

// --- Logs --- //
const getLogs = (params) => apiClient.get('/logs', { params });

// --- UCI --- //
const applyUciToDevice = (deviceId, commands) => apiClient.post(`/uci/devices/${deviceId}/apply`, { commands });

// --- Dashboard --- //
const getDashboardSummary = () => apiClient.get('/dashboard/summary'); // New


const api = {
    login,
    logout,
    checkAuthStatus,
    createUser,
    getDevices,
    getDevice,
    createDevice,
    updateDevice,
    deleteDevice,
    associateCredential,
    disassociateCredential,
    rebootDevice,
    refreshDeviceStatus,
    getLogConfig,
    toggleLogConfig,
    getCredentials,
    getCredential,
    createCredential,
    updateCredential,
    deleteCredential,
    verifyCredential,
    getLogs,
    applyUciToDevice,
    getDashboardSummary // Export new function
};

export default api; 