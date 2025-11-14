/**
 * FAMMO Location Service
 * Handles user location detection and clinic proximity
 */

class LocationService {
    constructor() {
        this.userLocation = null;
        this.permissionStatus = null;
    }

    /**
     * Get user's current location using browser Geolocation API
     * @returns {Promise<{latitude: number, longitude: number}>}
     */
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser'));
                return;
            }

            const options = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000 // Cache for 5 minutes
            };

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: position.timestamp
                    };
                    resolve(this.userLocation);
                },
                (error) => {
                    let errorMessage;
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage = "Location permission denied. Please enable location access in your browser settings.";
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage = "Location information is unavailable.";
                            break;
                        case error.TIMEOUT:
                            errorMessage = "Location request timed out.";
                            break;
                        default:
                            errorMessage = "An unknown error occurred while getting location.";
                    }
                    reject(new Error(errorMessage));
                },
                options
            );
        });
    }

    /**
     * Check if location permission is granted
     * @returns {Promise<boolean>}
     */
    async checkLocationPermission() {
        if ('permissions' in navigator) {
            try {
                const result = await navigator.permissions.query({ name: 'geolocation' });
                this.permissionStatus = result.state;
                return result.state === 'granted';
            } catch (error) {
                console.warn('Permission API not supported:', error);
                return false;
            }
        }
        return false;
    }

    /**
     * Calculate distance between two coordinates using Haversine formula
     * @param {number} lat1 - First latitude
     * @param {number} lon1 - First longitude
     * @param {number} lat2 - Second latitude
     * @param {number} lon2 - Second longitude
     * @returns {number} Distance in kilometers
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in kilometers
        const dLat = this.toRadians(lat2 - lat1);
        const dLon = this.toRadians(lon2 - lon1);
        
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;
        
        return Math.round(distance * 10) / 10; // Round to 1 decimal place
    }

    /**
     * Convert degrees to radians
     */
    toRadians(degrees) {
        return degrees * (Math.PI / 180);
    }

    /**
     * Get location from IP address as fallback (requires backend API)
     * @returns {Promise<{latitude: number, longitude: number, city: string}>}
     */
    async getLocationFromIP() {
        try {
            const response = await fetch('/api/location/ip/');
            if (response.ok) {
                return await response.json();
            }
            throw new Error('Failed to get location from IP');
        } catch (error) {
            console.error('IP location error:', error);
            throw error;
        }
    }

    /**
     * Save user location to localStorage
     */
    saveLocationToStorage(location) {
        localStorage.setItem('userLocation', JSON.stringify({
            ...location,
            savedAt: Date.now()
        }));
    }

    /**
     * Get saved location from localStorage
     * @param {number} maxAge - Maximum age in milliseconds (default: 1 hour)
     * @returns {Object|null}
     */
    getSavedLocation(maxAge = 3600000) {
        try {
            const saved = localStorage.getItem('userLocation');
            if (!saved) return null;

            const data = JSON.parse(saved);
            const age = Date.now() - data.savedAt;

            if (age > maxAge) {
                localStorage.removeItem('userLocation');
                return null;
            }

            return data;
        } catch (error) {
            console.error('Error reading saved location:', error);
            return null;
        }
    }

    /**
     * Format distance for display
     */
    formatDistance(km) {
        if (km < 1) {
            return `${Math.round(km * 1000)} m`;
        }
        return `${km} km`;
    }
}

// Create global instance
window.locationService = new LocationService();

/**
 * UI Helper: Show location request button
 */
function showLocationButton(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = options.className || 'btn-location';
    button.innerHTML = `
        <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        ${options.text || 'Use My Location'}
    `;

    button.addEventListener('click', async () => {
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> Getting location...';

        try {
            const location = await locationService.getCurrentLocation();
            locationService.saveLocationToStorage(location);
            
            if (options.onSuccess) {
                options.onSuccess(location);
            }

            // Update button to show success
            button.innerHTML = `
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Location Found
            `;
            button.className = options.successClassName || 'btn-success';
        } catch (error) {
            console.error('Location error:', error);
            button.innerHTML = `
                <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                ${error.message || 'Location Error'}
            `;
            button.className = options.errorClassName || 'btn-error';
            button.disabled = false;

            if (options.onError) {
                options.onError(error);
            }
        }
    });

    container.appendChild(button);
}
