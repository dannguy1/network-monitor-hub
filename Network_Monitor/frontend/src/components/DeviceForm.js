import React, { useState, useEffect } from 'react';

function DeviceForm({ initialDevice, onSubmit, onCancel }) {
    // Initialize form state either with initialDevice (for editing) or empty (for creating)
    const [formData, setFormData] = useState({
        name: '',
        ip_address: '',
        description: '',
    });

    // When initialDevice changes (e.g., when opening the form for editing), update the form data
    useEffect(() => {
        if (initialDevice) {
            setFormData({
                name: initialDevice.name || '',
                ip_address: initialDevice.ip_address || '',
                description: initialDevice.description || '',
            });
        } else {
            // Reset form when creating a new device or closing
            setFormData({ name: '', ip_address: '', description: '' });
        }
    }, [initialDevice]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // Basic validation
        if (!formData.name || !formData.ip_address) {
            alert('Name and IP Address are required.');
            return;
        }
        onSubmit(formData); // Pass the form data to the parent component's handler
    };

    return (
        <form onSubmit={handleSubmit} style={{ border: '1px dashed #ccc', padding: '15px', marginBottom: '15px' }}>
            <h3>{initialDevice ? 'Edit Device' : 'Add New Device'}</h3>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="name">Name: </label>
                <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                />
            </div>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="ip_address">IP Address: </label>
                <input
                    type="text"
                    id="ip_address"
                    name="ip_address"
                    value={formData.ip_address}
                    onChange={handleChange}
                    required
                />
            </div>
            <div style={{ marginBottom: '10px' }}>
                <label htmlFor="description">Description: </label>
                <textarea
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    rows="3"
                    style={{ width: '90%' }}
                />
            </div>
            <button type="submit" style={{ marginRight: '10px' }}>
                {initialDevice ? 'Update Device' : 'Create Device'}
            </button>
            <button type="button" onClick={onCancel}>
                Cancel
            </button>
        </form>
    );
}

export default DeviceForm; 