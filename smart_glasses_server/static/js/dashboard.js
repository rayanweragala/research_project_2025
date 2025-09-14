class DashboardManager {
    constructor() {
        this.startTime = new Date();
        this.services = [];
        this.currentService = 'overview';
        this.localIP = null;
        this.init();
    }

    async init() {
        console.log('Dashboard Manager: Initializing...');
        
        await this.loadSystemInfo();
        
        this.updateTime();
        this.checkAllServices();
        this.startPeriodicUpdates();
        this.bindEvents();
        
        console.log('Dashboard Manager: Initialization complete');
        console.log('Services:', this.services);
    }

    async loadSystemInfo() {
        try {
            console.log('Dashboard Manager: Loading system information...');
            const response = await fetch('/api/system/info');
            const systemInfo = await response.json();
            
            this.localIP = systemInfo.local_ip;
            console.log(`Dashboard Manager: Local IP detected as ${this.localIP}`);
            
            this.services = [
                { 
                    id: 'face', 
                    name: 'Face Recognition', 
                    url: `http://${this.localIP}:5000`, 
                    port: 5000, 
                    status: false 
                },
                { 
                    id: 'ocr', 
                    name: 'OCR Service', 
                    url: `http://${this.localIP}:5002`, 
                    port: 5002, 
                    status: false 
                },
                { 
                    id: 'ultrasonic', 
                    name: 'Distance Sensor', 
                    url: `http://${this.localIP}:5001`, 
                    port: 5001, 
                    status: false 
                }
            ];
            
            this.updateIframeUrls();
            
        } catch (error) {
            console.error('Dashboard Manager: Failed to load system info:', error);
            this.localIP = window.location.hostname;
            this.services = [
                { id: 'face', name: 'Face Recognition', url: `http://${this.localIP}:5000`, port: 5000, status: false },
                { id: 'ocr', name: 'OCR Service', url: `http://${this.localIP}:5002`, port: 5002, status: false },
                { id: 'ultrasonic', name: 'Distance Sensor', url: `http://${this.localIP}:5001`, port: 5001, status: false }
            ];
        }
    }

    updateIframeUrls() {
        console.log('Dashboard Manager: Updating iframe URLs...');
        this.services.forEach(service => {
            const iframe = document.getElementById(service.id);
            if (iframe) {
                iframe.setAttribute('data-src', service.url);
                console.log(`Dashboard Manager: Set ${service.id} iframe URL to ${service.url}`);
            }
        });
    }

    bindEvents() {
        console.log('Dashboard Manager: Binding events...');
        
        window.addEventListener('beforeunload', () => {
            console.log('Dashboard Manager: Page unloading, cleaning up iframes...');
            this.services.forEach(service => {
                const iframe = document.getElementById(service.id);
                if (iframe && iframe.src !== 'about:blank') {
                    iframe.src = 'about:blank';
                }
            });
        });

        window.addEventListener('error', (e) => {
            console.error('Dashboard Manager: Window error:', e.error);
        });
    }

    showService(serviceId) {
        if (this.currentService === serviceId) {
            console.log(`Dashboard Manager: Already showing ${serviceId}`);
            return;
        }

        console.log(`Dashboard Manager: Switching to service: ${serviceId}`);

        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        const clickedTab = Array.from(document.querySelectorAll('.nav-tab'))
            .find(tab => {
                const tabText = tab.textContent.toLowerCase();
                if (serviceId === 'overview') return tabText === 'overview';
                if (serviceId === 'face') return tabText.includes('face');
                if (serviceId === 'ocr') return tabText.includes('ocr');
                if (serviceId === 'ultrasonic') return tabText.includes('distance') || tabText.includes('sensor');
                return false;
            });
        
        if (clickedTab) {
            clickedTab.classList.add('active');
        }

        document.querySelectorAll('.service-frame').forEach(frame => {
            frame.classList.remove('active');
        });

        const targetFrame = document.getElementById(serviceId);
        if (targetFrame) {
            targetFrame.classList.add('active');
            
            if (serviceId !== 'overview' && targetFrame.tagName === 'IFRAME') {
                const dataSrc = targetFrame.getAttribute('data-src');
                if (dataSrc && targetFrame.src === 'about:blank') {
                    console.log(`Dashboard Manager: Loading ${serviceId} service from ${dataSrc}`);
                    targetFrame.src = dataSrc;
                    
                    targetFrame.onload = () => {
                        console.log(`Dashboard Manager: ${serviceId} service loaded successfully`);
                    };
                    
                    targetFrame.onerror = () => {
                        console.error(`Dashboard Manager: Failed to load ${serviceId} service`);
                    };
                }
            }
        }

        this.currentService = serviceId;
        const serviceName = serviceId === 'overview' ? 'Overview' : this.getServiceName(serviceId);
        console.log(`Dashboard Manager: Switched to ${serviceName}`);
    }

    getServiceName(serviceId) {
        const service = this.services.find(s => s.id === serviceId);
        return service ? service.name : serviceId;
    }

    openInNew(url) {
        console.log(`Dashboard Manager: Opening ${url} in new window`);
        const features = 'width=1200,height=800,scrollbars=yes,resizable=yes,toolbar=no,menubar=no,location=no,status=no';
        const newWindow = window.open(url, '_blank', features);
        
        if (newWindow) {
            console.log(`Dashboard Manager: Successfully opened ${url} in new window`);
        } else {
            console.error('Dashboard Manager: Pop-up blocked');
            alert('Pop-up blocked. Please allow pop-ups for this site.');
        }
    }

    async checkServiceStatus(service) {
        const startTime = Date.now();
        console.log(`Dashboard Manager: Checking status of ${service.name} at ${service.url}`);
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                console.log(`Dashboard Manager: Timeout checking ${service.name}`);
                controller.abort();
            }, 5000);

            let response;
            try {
                response = await fetch(`${service.url}/api/health`, {
                    method: 'GET',
                    signal: controller.signal,
                    mode: 'cors'
                });
                console.log(`Dashboard Manager: ${service.name} health check response: ${response.status}`);
            } catch (corsError) {
                console.log(`Dashboard Manager: CORS failed for ${service.name}, trying no-cors...`);
                response = await fetch(service.url, {
                    method: 'GET',
                    signal: controller.signal,
                    mode: 'no-cors'
                });
            }

            clearTimeout(timeoutId);
            
            const responseTime = Date.now() - startTime;
            if (response.ok || response.type === 'opaque') {
                service.status = true;
                console.log(`Dashboard Manager: ${service.name} is ONLINE (${responseTime}ms)`);
                this.updateServiceStatusUI(service, true, 'Online');
            } else {
                service.status = false;
                console.log(`Dashboard Manager: ${service.name} is OFFLINE - status: ${response.status}`);
                this.updateServiceStatusUI(service, false, 'Offline');
            }
        } catch (error) {
            service.status = false;
            const responseTime = Date.now() - startTime;
            
            if (error.name === 'AbortError') {
                console.log(`Dashboard Manager: ${service.name} TIMEOUT after ${responseTime}ms`);
                this.updateServiceStatusUI(service, false, 'Timeout');
            } else {
                console.log(`Dashboard Manager: ${service.name} ERROR - ${error.message}`);
                this.updateServiceStatusUI(service, false, 'Offline');
            }
        }
    }

    updateServiceStatusUI(service, isOnline, statusText) {
        const elements = [
            `${service.id}StatusIndicator`,
            `${service.id}FooterStatus`
        ];

        elements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.className = `status-indicator ${isOnline ? 'status-online' : 'status-offline'}`;
            }
        });

        const textElements = [
            `${service.id}StatusText`,
            `${service.id}FooterText`
        ];

        textElements.forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = statusText;
            }
        });

        this.updateServiceButtons(service, isOnline);
    }

    updateServiceButtons(service, isOnline) {
        const buttons = document.querySelectorAll(`button[onclick*="${service.id}"]`);
        buttons.forEach(button => {
            if (button.textContent.includes('Open Interface')) {
                button.disabled = !isOnline;
                button.style.opacity = isOnline ? '1' : '0.6';
                if (!isOnline) {
                    button.title = `${service.name} is currently offline`;
                } else {
                    button.title = `Open ${service.name}`;
                }
            }
        });
    }

    async checkAllServices() {
        console.log('Dashboard Manager: Checking all services status...');
        const startTime = Date.now();
        
        const promises = this.services.map(service => this.checkServiceStatus(service));
        const results = await Promise.allSettled(promises);
        
        const totalTime = Date.now() - startTime;
        console.log(`Dashboard Manager: Service status check completed in ${totalTime}ms`);
        
        results.forEach((result, index) => {
            if (result.status === 'rejected') {
                console.error(`Dashboard Manager: Failed to check ${this.services[index].name}:`, result.reason);
            }
        });
        
        this.updateActiveServicesCount();
    }

    updateActiveServicesCount() {
        const activeCount = this.services.filter(s => s.status).length;
        const element = document.getElementById('activeServices');
        if (element) {
            element.textContent = activeCount.toString();
        }
        console.log(`Dashboard Manager: ${activeCount}/${this.services.length} services are active`);
    }

    updateTime() {
        const now = new Date();
        const timeElement = document.getElementById('currentTime');
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }

    updateUptime() {
        const now = new Date();
        const uptime = new Date(now - this.startTime);
        const hours = String(uptime.getUTCHours()).padStart(2, '0');
        const minutes = String(uptime.getUTCMinutes()).padStart(2, '0');
        const seconds = String(uptime.getUTCSeconds()).padStart(2, '0');
        
        const element = document.getElementById('systemUptime');
        if (element) {
            element.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }

    startPeriodicUpdates() {
        console.log('Dashboard Manager: Starting periodic updates...');
        
        setInterval(() => this.updateTime(), 1000);
        
        setInterval(() => this.updateUptime(), 1000);
        
        setInterval(() => {
            console.log('Dashboard Manager: Periodic service check...');
            this.checkAllServices();
        }, 30000);
    }

    refreshServices() {
        console.log('Dashboard Manager: Manual service refresh requested');
        this.checkAllServices();
    }

    getSystemInfo() {
        const info = {
            uptime: new Date() - this.startTime,
            activeServices: this.services.filter(s => s.status).length,
            totalServices: this.services.length,
            localIP: this.localIP,
            services: this.services
        };
        console.log('Dashboard Manager: System info requested', info);
        return info;
    }
}

function showService(serviceId) {
    console.log(`Global: showService called with ${serviceId}`);
    if (window.dashboard) {
        window.dashboard.showService(serviceId);
    } else {
        console.error('Global: Dashboard not initialized');
    }
}

function openInNew(url) {
    console.log(`Global: openInNew called with ${url}`);
    if (window.dashboard) {
        window.dashboard.openInNew(url);
    } else {
        console.error('Global: Dashboard not initialized');
    }
}

function refreshServices() {
    console.log('Global: refreshServices called');
    if (window.dashboard) {
        window.dashboard.refreshServices();
    } else {
        console.error('Global: Dashboard not initialized');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing Dashboard...');
    try {
        window.dashboard = new DashboardManager();
        console.log('Dashboard initialization started');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
    }
});

document.addEventListener('visibilitychange', function() {
    if (window.dashboard && !document.hidden) {
        console.log('Page became visible - refreshing service status');
        window.dashboard.checkAllServices();
    }
});

window.debugDashboard = function() {
    if (window.dashboard) {
        console.log('Dashboard Debug Info:', window.dashboard.getSystemInfo());
    } else {
        console.log('Dashboard not initialized');
    }
};