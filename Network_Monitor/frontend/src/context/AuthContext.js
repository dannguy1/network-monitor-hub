import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import api from '../services/api';

// Create the context
const AuthContext = createContext(null);

// Create a provider component
export const AuthProvider = ({ children }) => {
    const [currentUser, setCurrentUser] = useState(null);
    const [loadingAuth, setLoadingAuth] = useState(true);
    const [authError, setAuthError] = useState(null); // For login/logout errors

    // Check auth status on initial load (memoized)
    const checkAuthStatus = useCallback(async () => {
        setLoadingAuth(true);
        try {
            const response = await api.getAuthStatus();
            setCurrentUser(response.data.user);
            setAuthError(null);
        } catch (err) {
            console.debug('Auth check failed or user not logged in.');
            setCurrentUser(null);
            // Don't set authError here, as 401 is expected if not logged in
        } finally {
            setLoadingAuth(false);
        }
    }, []);

    useEffect(() => {
        checkAuthStatus();
    }, [checkAuthStatus]);

    // Login function
    const login = async (username, password) => {
        setAuthError(null);
        setLoadingAuth(true); // Indicate loading during login attempt
        try {
            const response = await api.login({ username, password });
            setCurrentUser(response.data);
            setLoadingAuth(false);
            return true; // Indicate success
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Login failed. Please check credentials.';
            console.error("Login error:", errorMsg);
            setAuthError(errorMsg);
            setCurrentUser(null);
            setLoadingAuth(false);
            return false; // Indicate failure
        }
    };

    // Logout function
    const logout = async () => {
        setAuthError(null);
        try {
            await api.logout();
            setCurrentUser(null);
        } catch (err) {
            console.error("Logout failed:", err);
            setAuthError('Logout failed. Please try again.');
            // Keep user logged in locally on logout failure? Or force clear?
            // setCurrentUser(null); // Option: clear local state even if backend fails
        }
    };

    // The value provided to consuming components
    const value = {
        currentUser,
        loadingAuth,
        authError,
        login,
        logout,
        checkAuthStatus // Expose check function if needed elsewhere
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

// Custom hook to use the auth context
export const useAuth = () => {
    return useContext(AuthContext);
}; 