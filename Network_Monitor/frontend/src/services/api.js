import axios from 'axios';

// Base URL for the backend API
// In development, React's proxy will handle redirecting this
// In production, Nginx or similar should route /api/v1 to the backend
const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a response interceptor to handle 401 errors globally
apiClient.interceptors.response.use(
    response => response, // Pass through successful responses
    error => {
        if (error.response && error.response.status === 401) {
            // Check if it's not the /auth/status or /auth/login endpoints that failed
            if (!error.config.url.includes('/auth/status') && !error.config.url.includes('/auth/login')) {
                console.warn('Unauthorized (401). Redirecting to login or clearing session.');
                // Option 1: Redirect to login (might cause issues if App component isn't ready)
                // window.location.href = '/login'; // Or your login route
                
                // Option 2: Emit an event or use context to notify App component to clear user state
                // This is generally safer within React.
                // For simplicity here, we'll just log it. App component's check on load handles initial state.
                // A more robust solution involves React Context for auth state management.
            }
        }
        // Important: Reject the promise so individual calls can still catch errors
        return Promise.reject(error);
    }
);

// --- Device Endpoints --- 
export const getDevices = () => apiClient.get('/devices');
export const getDevice = (id) => apiClient.get(`/devices/${id}`);
export const createDevice = (deviceData) => apiClient.post('/devices', deviceData);
export const updateDevice = (id, deviceData) => apiClient.put(`/devices/${id}`, deviceData);
export const deleteDevice = (id) => apiClient.delete(`/devices/${id}`);
export const applyDeviceConfig = (id, configData) => apiClient.post(`/devices/${id}/apply_config`, { config_data: configData });

// --- Credential Endpoints --- 
export const getCredentials = () => apiClient.get('/credentials');
export const getCredential = (id) => apiClient.get(`/credentials/${id}`);
export const createCredential = (credentialData) => apiClient.post('/credentials', credentialData);
export const updateCredential = (id, credentialData) => apiClient.put(`/credentials/${id}`, credentialData);
export const deleteCredential = (id) => apiClient.delete(`/credentials/${id}`);
export const associateCredential = (deviceId, credentialId) => apiClient.post(`/devices/${deviceId}/credential/${credentialId}`);
export const disassociateCredential = (deviceId) => apiClient.delete(`/devices/${deviceId}/credential`);
export const verifyCredential = (id) => apiClient.post(`/credentials/${id}/verify`);

// --- Log Endpoints --- 
// params is an object like { page: 1, per_page: 50, device_id: 1, ... }
export const getLogs = (params) => apiClient.get('/logs', { params });
export const getLogEntry = (id) => apiClient.get(`/logs/${id}`);

// --- UCI Endpoints --- 
export const generateUci = (generationData) => apiClient.post('/uci/generate');

// --- Auth Endpoints --- 
export const login = (credentials) => apiClient.post('/auth/login', credentials);
export const logout = () => apiClient.post('/auth/logout');
export const getAuthStatus = () => apiClient.get('/auth/status');

// --- Log Config Endpoints ---
export const getLogConfig = (deviceId) => apiClient.get(`/devices/${deviceId}/log_config`);
export const setLogConfig = (deviceId, enable) => apiClient.post(`/devices/${deviceId}/log_config`, { enable });

// --- Reboot Endpoint ---
export const rebootDevice = (deviceId) => apiClient.post(`/devices/${deviceId}/reboot`);

// --- Refresh Status Endpoint ---
export const refreshDeviceStatus = (deviceId) => apiClient.post(`/devices/${deviceId}/refresh_status`);

// Add other endpoints as needed

export default {
    getDevices,
    getDevice,
    createDevice,
    updateDevice,
    deleteDevice,
    applyDeviceConfig,
    getCredentials,
    getCredential,
    createCredential,
    updateCredential,
    deleteCredential,
    associateCredential,
    disassociateCredential,
    verifyCredential,
    getLogs,
    getLogEntry,
    generateUci,
    login,
    logout,
    getAuthStatus,
    getLogConfig,
    setLogConfig,
    rebootDevice,
    refreshDeviceStatus,
}; 