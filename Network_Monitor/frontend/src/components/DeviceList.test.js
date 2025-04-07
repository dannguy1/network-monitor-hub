import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DeviceList from './DeviceList';
import api from '../services/api'; // We need to mock API calls

// Mock the API service
jest.mock('../services/api');

// Mock child components that might interfere or aren't needed for this test
jest.mock('./DeviceForm', () => () => <div data-testid="device-form-mock">Device Form Mock</div>);
jest.mock('./ApplyUciModal', () => () => <div data-testid="uci-modal-mock">UCI Modal Mock</div>);

describe('DeviceList Component', () => {
    beforeEach(() => {
        // Reset mocks before each test
        api.getDevices.mockClear();
        api.getCredentials.mockClear();
    });

    test('renders loading state initially', () => {
        // Mock pending promises
        api.getDevices.mockResolvedValueOnce({ data: [] });
        api.getCredentials.mockResolvedValueOnce({ data: [] });
        render(<DeviceList />);
        expect(screen.getByText(/Loading devices and credentials.../i)).toBeInTheDocument();
    });

    test('renders device information after successful fetch', async () => {
        const mockDevices = [
            { id: 1, name: 'Router1', ip_address: '192.168.1.1', status: 'Online', description: 'Main Router', last_seen: new Date().toISOString(), credential_id: null },
            { id: 2, name: 'AP1', ip_address: '192.168.1.2', status: 'Offline', description: null, last_seen: null, credential_id: 10 },
        ];
        const mockCredentials = [
             { id: 10, name: 'admin-cred', ssh_username: 'root'} // Needed for getCredentialName
        ];

        api.getDevices.mockResolvedValueOnce({ data: mockDevices });
        api.getCredentials.mockResolvedValueOnce({ data: mockCredentials });

        render(<DeviceList />);

        // Wait for the loading text to disappear
        await waitFor(() => {
            expect(screen.queryByText(/Loading devices and credentials.../i)).not.toBeInTheDocument();
        });

        // Check if device names are rendered
        expect(screen.getByText(/Router1/i)).toBeInTheDocument();
        expect(screen.getByText(/192.168.1.1/i)).toBeInTheDocument();
        expect(screen.getByText(/AP1/i)).toBeInTheDocument();
        expect(screen.getByText(/192.168.1.2/i)).toBeInTheDocument();
        
        // Check if status is rendered (using badge text)
        expect(screen.getByText('Online')).toBeInTheDocument();
        expect(screen.getByText('Offline')).toBeInTheDocument();

        // Check credential association text
        expect(screen.getByText(/admin-cred/i)).toBeInTheDocument(); // For AP1
        // Check if select element is present for Router1 (no credential)
        expect(screen.getByRole('combobox')).toBeInTheDocument(); 
    });

    test('displays error message on fetch failure', async () => {
        const errorMessage = 'Network Error';
        api.getDevices.mockRejectedValueOnce(new Error(errorMessage));
        api.getCredentials.mockResolvedValueOnce({ data: [] }); // Assume credentials load ok

        render(<DeviceList />);

        await waitFor(() => {
            expect(screen.getByText(new RegExp(`Error loading data: ${errorMessage}`, 'i'))).toBeInTheDocument();
        });
    });

    // Add more tests for actions like delete, open form, associate etc.
}); 