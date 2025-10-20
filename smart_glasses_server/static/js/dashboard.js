// Smart Glasses Dashboard JavaScript
let startTime = Date.now();
let healthCheckInterval;

const SERVICES = {
    face: {
        name: 'Face Recognition',
        url: 'http://localhost:5000',
        healthEndpoint: '/api/health',
        port: 5000
    },
    object: {
        name: 'Object Detection',
        url: 'http://localhost:5005',
        healthEndpoint: '/api/health',
        port: 5005
    },
    ocr: {
        name: 'OCR Processing',
        url: 'http://localhost:5002',
        healthEndpoint: '/api/health',
        port: 5002
    },
    ultrasonic: {
        name: 'Distance Sensor',
        url: 'http://localhost:5001',
        healthEndpoint: '/api/health',
        port: 5001
    }
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('Smart Glasses Dashboard initialized');
    updateClock();
    setInterval(updateClock, 1000);
    updateUptime();
    setInterval(updateUptime, 1000);
    
    checkAllServicesHealth();
    healthCheckInterval = setInterval(checkAllServicesHealth, 10000);
});

function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

function updateUptime() {
    const elapsed = Date.now() - startTime;
    const hours = Math.floor(elapsed / 3600000);
    const minutes = Math.floor((elapsed % 3600000) / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    
    const uptimeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    const uptimeElement = document.getElementById('systemUptime');
    if (uptimeElement) {
        uptimeElement.textContent = uptimeString;
    }
}

function showService(serviceName) {
    const frames = document.querySelectorAll('.service-frame');
    frames.forEach(frame => {
        frame.classList.remove('active');
    });
    
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    const selectedFrame = document.getElementById(serviceName);
    if (selectedFrame) {
        selectedFrame.classList.add('active');
        
        if (serviceName !== 'overview' && selectedFrame.tagName === 'IFRAME') {
            const dataSrc = selectedFrame.getAttribute('data-src');
            if (selectedFrame.src === 'about:blank' && dataSrc) {
                selectedFrame.src = dataSrc;
            }
        }
    }
    
    const activeTab = Array.from(tabs).find(tab => 
        tab.textContent.toLowerCase().includes(serviceName) || 
        tab.getAttribute('onclick').includes(`'${serviceName}'`)
    );
    if (activeTab) {
        activeTab.classList.add('active');
    }
}

function openInNew(url) {
    window.open(url, '_blank', 'width=1200,height=800');
}

async function checkAllServicesHealth() {
    let activeCount = 0;
    
    for (const [key, service] of Object.entries(SERVICES)) {
        const isOnline = await checkServiceHealth(key, service);
        if (isOnline) {
            activeCount++;
        }
    }
    
    const activeServicesElement = document.getElementById('activeServices');
    if (activeServicesElement) {
        activeServicesElement.textContent = activeCount;
    }
}

async function checkServiceHealth(serviceName, serviceConfig) {
    try {
        const response = await fetch(serviceConfig.url + serviceConfig.healthEndpoint, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache'
        });
        
        if (response.ok) {
            const data = await response.json();
            updateServiceStatus(serviceName, 'online', 'Online');
            console.log(`${serviceConfig.name} is online`);
            return true;
        } else {
            updateServiceStatus(serviceName, 'offline', 'Offline');
            return false;
        }
    } catch (error) {
        updateServiceStatus(serviceName, 'offline', 'Offline');
        return false;
    }
}

function updateServiceStatus(serviceName, status, statusText) {
    const cardIndicator = document.getElementById(`${serviceName}StatusIndicator`);
    const cardStatusText = document.getElementById(`${serviceName}StatusText`);
    
    if (cardIndicator) {
        cardIndicator.classList.remove('status-online', 'status-offline');
        cardIndicator.classList.add(`status-${status}`);
    }
    
    if (cardStatusText) {
        cardStatusText.textContent = statusText;
    }
    
    const footerIndicator = document.getElementById(`${serviceName}FooterStatus`);
    const footerStatusText = document.getElementById(`${serviceName}FooterText`);
    
    if (footerIndicator) {
        footerIndicator.classList.remove('status-online', 'status-offline');
        footerIndicator.classList.add(`status-${status}`);
    }
    
    if (footerStatusText) {
        footerStatusText.textContent = statusText;
    }
}

window.addEventListener('beforeunload', function() {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
});

console.log('%c Smart Glasses Development Console ', 'background: #2563eb; color: white; font-size: 16px; padding: 10px;');
console.log('%c Available Services:', 'font-weight: bold; font-size: 14px;');
Object.entries(SERVICES).forEach(([key, service]) => {
    console.log(`  ${service.name}: ${service.url}`);
});