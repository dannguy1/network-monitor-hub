import pytest
from app import create_app, db # Adjust import path if needed

@pytest.fixture(scope='module')
def test_client():
    # Create a Flask app configured for testing
    flask_app = create_app('testing')

    # Establish an application context
    with flask_app.app_context():
        # Create the database and the database table(s)
        db.create_all()

        # Create a test client using the Flask application configured for testing
        with flask_app.test_client() as testing_client:
            yield testing_client # this is where the testing happens!
        
        # Teardown: drop all tables after tests are done
        db.drop_all()

def test_home_page(test_client):
    """ Test the basic API ping or a known endpoint. """
    # Test a simple API endpoint (e.g., the /api/v1/devices GET endpoint)
    response = test_client.get('/api/v1/devices')
    assert response.status_code == 200
    assert b'[]' in response.data # Assuming initially no devices

# Add more tests here for models, API endpoints, services etc.
# Example test for device creation API:
# def test_create_device_api(test_client):
#     response = test_client.post('/api/v1/devices', json={
#         'name': 'Test Device',
#         'ip_address': '192.168.1.100'
#     })
#     assert response.status_code == 201
#     assert b'Test Device' in response.data
#     assert b'192.168.1.100' in response.data
# 
#     # Verify device exists in DB (requires importing Device model)
#     from app.models import Device
#     device = Device.query.filter_by(name='Test Device').first()
#     assert device is not None
#     assert device.ip_address == '192.168.1.100' 