let recognitionActive = false;
let recognitionInterval;
let currentStats = {};

function showToast(message, type = 'info', title = '', duration = 4000) {
const toastContainer = document.getElementById('toastContainer');
const toast = document.createElement('div');
toast.className = `toast ${type}`;

    const icons = {
success: '',
error: '',
warning: '',
info: ''
};

const titles = {
    success: title || 'Success',
    error: title || 'Error',
    warning: title || 'Warning', 
    info: title || 'Information'
};

toast.innerHTML = `
    <div class="toast-header">
        <span>${icons[type]} ${titles[type]}</span>
        <button class="toast-close" onclick="closeToast(this)">&times;</button>
    </div>
    <div class="toast-message">${message}</div>
`;

toastContainer.appendChild(toast);

setTimeout(() => toast.classList.add('show'), 100);

setTimeout(() => {
    if (toast.parentNode) {
        closeToast(toast.querySelector('.toast-close'));
    }
}, duration);
}

function closeToast(button) {
const toast = button.closest('.toast');
toast.classList.remove('show');
setTimeout(() => {
    if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
    }
}, 400);
}

function switchTab(event, tabName) {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const tabContent = document.getElementById(tabName + '-tab');
    if (tabContent) {
        tabContent.classList.add('active');
    }

    if (event && event.target) {
        event.target.classList.add('active');
    }

    switch(tabName) {
        case 'analytics':
            loadAnalytics();
            break;
        case 'reports':
            setDefaultReportDate();
            loadDailyReport();
            break;
        case 'people':
            loadPeopleList();
            break;
    }
}


function startRecognition() {
if (!recognitionActive) {
recognitionActive = true;
document.getElementById('status').innerHTML = '<span class="loading-spinner"></span>Initializing camera system...';
document.getElementById('status').className = 'status warning';

fetch('/api/camera/start', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('status').innerHTML = 'Recognition System Active';
            document.getElementById('status').className = 'status success';
            recognitionInterval = setInterval(getServerFrame, 1000);
            showToast('Camera system initialized successfully', 'success', 'System Started');
        } else {
            document.getElementById('status').innerHTML = 'Error: ' + data.message;
            document.getElementById('status').className = 'status error';
            recognitionActive = false;
            showToast(data.message, 'error', 'Initialization Failed');
        }
    })
    .catch(err => {
        document.getElementById('status').innerHTML = 'Connection Error';
        document.getElementById('status').className = 'status error';
        recognitionActive = false;
        showToast('Failed to connect to camera server', 'error', 'Connection Error');
    });
}
}

function stopRecognition() {
recognitionActive = false;
document.getElementById('status').innerHTML = '<span class="loading-spinner"></span>Terminating camera system...';

if (recognitionInterval) {
clearInterval(recognitionInterval);
}

fetch('/api/camera/stop', { method: 'POST' })
.then(() => {
    document.getElementById('status').innerHTML = 'Recognition System Terminated';
    document.getElementById('status').className = 'status warning';
    showToast('Recognition system terminated successfully', 'info', 'System Stopped');
})
.catch(() => {
    document.getElementById('status').innerHTML = 'Recognition System Terminated';
    document.getElementById('status').className = 'status warning';
    showToast('Recognition system terminated (connection lost)', 'warning', 'System Stopped');
});
}

function getServerFrame() {
if (!recognitionActive) return;

fetch('/api/camera/frame')
.then(response => {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
})
.then(data => {
    if (data.image) {
        const cameraFeed = document.getElementById('cameraFeed');
        if (cameraFeed) {
            cameraFeed.src = 'data:image/jpeg;base64,' + data.image;
        }
        displayResult(data);
        updateCurrentResult(data);
    } else if (data.error) {
        displayResult({
            recognized: false,
            name: null,
            confidence: 0,
            message: data.error,
            quality_score: 0,
            processing_time: 0,
            error: true
        });
    }
})
.catch(err => {
    console.error('Frame error:', err);
    displayResult({
        recognized: false,
        name: null,
        confidence: 0,
        message: `Connection error: ${err.message}`,
        quality_score: 0,
        processing_time: 0,
        error: true
    });
});
}

function updateCurrentResult(data) {
const currentResult = document.getElementById('currentResult');
if (!data.recognized && !data.error) {
currentResult.innerHTML = `
    <div style="padding: 18px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px; margin-top: 18px; border-left: 4px solid #6c757d;">
        <div style="font-weight: 600; color: #495057; font-size: 1.1em;">Unknown Person</div>
        <div style="font-size: 0.95em; margin-top: 8px; color: #6c757d;">
            Quality: ${(data.quality_score * 100).toFixed(1)}%
            ${data.method_used ? ` • Method: ${formatMethod(data.method_used)}` : ''}
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${(data.confidence * 100)}%; background: #ff9800;"></div>
        </div>
    </div>
`;
} else if (data.recognized) {
currentResult.innerHTML = `
    <div style="padding: 18px; background: linear-gradient(135deg, #e8f5e8, #f1f8e9); border-radius: 12px; margin-top: 18px; border-left: 4px solid #4caf50;">
        <div style="font-weight: 700; color: #2e7d32; font-size: 1.2em;">
            ${data.name}
            <span class="confidence-level conf-${data.confidence_level}">${formatConfidenceLevel(data.confidence_level)}</span>
        </div>
        <div style="font-size: 0.95em; margin-top: 10px; color: #4caf50; font-weight: 500;">
            Confidence: ${(data.confidence * 100).toFixed(1)}% • 
            Quality: ${(data.quality_score * 100).toFixed(1)}%
            ${data.method_used ? ` • ${formatMethod(data.method_used)}` : ''}
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${(data.confidence * 100)}%;"></div>
        </div>
    </div>
`;
} else if (data.error) {
currentResult.innerHTML = `
    <div style="padding: 18px; background: linear-gradient(135deg, #ffebee, #fce4ec); border-radius: 12px; margin-top: 18px; border-left: 4px solid #f44336;">
        <div style="font-weight: 600; color: #c62828; font-size: 1.1em;">Error: ${data.message}</div>
    </div>
`;
}
}

function displayResult(data) {
let resultsDiv = document.getElementById('results');
let resultClass = data.error ? 'error' : (data.recognized ? 'recognized' : 'unknown');

let confidence = data.confidence || 0;
let quality = data.quality_score || 0;
let processingTime = data.processing_time || 0;

let message = data.error ? 
`${data.message}` :
(data.recognized ? 
    `${data.name}` :
    `Unknown person`);

let confidenceLevel = data.confidence_level || 'unknown';
let methodUsed = data.method_used || 'standard';

let resultHtml = `
<div class="recognition-result ${resultClass}">
    <div class="result-header">
        ${new Date().toLocaleTimeString()} - ${message}
        ${data.recognized ? `<span class="confidence-level conf-${confidenceLevel}">${formatConfidenceLevel(confidenceLevel)}</span>` : ''}
    </div>
    <div class="result-details">
        Confidence: ${(confidence * 100).toFixed(1)}% • 
        Quality: ${(quality * 100).toFixed(1)}% • 
        Processing: ${(processingTime * 1000).toFixed(0)}ms • 
        Method: ${formatMethod(methodUsed)}
    </div>
    <div class="confidence-bar">
        <div class="confidence-fill" style="width: ${(confidence * 100)}%; ${!data.recognized ? 'background: #ff9800;' : ''}"></div>
    </div>
</div>
`;

resultsDiv.innerHTML = resultHtml + resultsDiv.innerHTML;

let results = resultsDiv.children;
while (results.length > 10) {
resultsDiv.removeChild(results[results.length - 1]);
}
}

function loadAnalytics() {
fetch('/api/analytics_enhanced')
.then(response => {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
})
.then(data => {
    currentStats = data;
    updateAnalyticsDisplay(data);
})
.catch(err => {
    console.error('Analytics error:', err);
    showToast('Failed to load analytics data', 'error', 'Analytics Error');
    
    const analyticsElements = ['recognitionRate', 'avgTime', 'totalRequests', 'enhancedMethods'];
    analyticsElements.forEach(elementId => {
        const element = document.getElementById(elementId);
        if (element) element.textContent = '0';
    });
});
}

function updateAnalyticsDisplay(data) {
if (data && data.recognition_stats) {
let stats = data.recognition_stats;
let rate = stats.total_requests > 0 ? 
    (stats.successful_recognitions / stats.total_requests * 100).toFixed(1) : 0;

const recognitionRateEl = document.getElementById('recognitionRate');
const avgTimeEl = document.getElementById('avgTime');
const totalRequestsEl = document.getElementById('totalRequests');
const enhancedMethodsEl = document.getElementById('enhancedMethods');

if (recognitionRateEl) recognitionRateEl.textContent = rate + '%';
if (avgTimeEl) avgTimeEl.textContent = (stats.avg_processing_time * 1000).toFixed(0) + 'ms';
if (totalRequestsEl) totalRequestsEl.textContent = stats.total_requests;

let enhancedCount = (stats.weighted_average_applied || 0) + 
                  (stats.temporal_smoothing_applied || 0) + 
                  (stats.outliers_removed || 0);
if (enhancedMethodsEl) enhancedMethodsEl.textContent = enhancedCount;
}

if (data && data.method_usage) {
updateMethodChart(data.method_usage);
}

if (data && data.recent_recognitions) {
updateConfidenceChart(data.recent_recognitions);
}

if (data && data.hourly_distribution) {
updateHourlyChart(data.hourly_distribution);
}
}

function updateMethodChart(methodData) {
const chartDiv = document.getElementById('methodChart');
const total = Object.values(methodData).reduce((a, b) => a + b, 0);

if (total === 0) {
chartDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Method Data Available</h3>
        <p>Method usage statistics will appear here once recognition activities begin.</p>
    </div>
`;
return;
}

let html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">';

Object.entries(methodData).forEach(([method, count]) => {
const percentage = ((count / total) * 100).toFixed(1);
html += `
    <div class="method-badge method-${method.split('_')[0]}" style="flex: 1; min-width: 140px; text-align: center; padding: 15px;">
        ${formatMethod(method)}<br>
        <strong>${count} (${percentage}%)</strong>
    </div>
`;
});

html += '</div>';
chartDiv.innerHTML = html;
}

function updateConfidenceChart(recognitions) {
const chartDiv = document.getElementById('confidenceChart');

if (!recognitions || recognitions.length === 0) {
chartDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Confidence Data Available</h3>
        <p>Confidence level distribution will be displayed here after recognition activities.</p>
    </div>
`;
return;
}

const levels = { very_high: 0, high: 0, medium: 0, low: 0, very_low: 0 };

recognitions.forEach(rec => {
if (rec.confidence_level) {
    levels[rec.confidence_level]++;
}
});

const total = Object.values(levels).reduce((a, b) => a + b, 0);

let html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">';

Object.entries(levels).forEach(([level, count]) => {
const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
html += `
    <div class="confidence-level conf-${level}" style="flex: 1; min-width: 120px; text-align: center; padding: 18px;">
        <strong>${count}</strong><br>
        ${formatConfidenceLevel(level)}<br>
        <small>(${percentage}%)</small>
    </div>
`;
});

html += '</div>';
chartDiv.innerHTML = html;
}

function updateHourlyChart(hourlyData) {
const chartDiv = document.getElementById('hourlyChart');

if (!hourlyData || Object.keys(hourlyData).length === 0) {
chartDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Hourly Data Available</h3>
        <p>24-hour activity patterns will be shown here after collecting usage data.</p>
    </div>
`;
return;
}

const maxValue = Math.max(...Object.values(hourlyData));

let html = '<div style="display: flex; align-items: end; gap: 4px; height: 180px; padding: 20px 0;">';

for (let hour = 0; hour < 24; hour++) {
const count = hourlyData[hour] || 0;
const height = maxValue > 0 ? (count / maxValue) * 140 : 0;

html += `
    <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
        <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); 
                    width: 100%; height: ${height}px; border-radius: 3px; 
                    margin-bottom: 8px; min-height: 3px;
                    ${count > 0 ? `title='${count} recognitions at ${hour}:00'` : ''}
                    box-shadow: 0 2px 8px rgba(79, 172, 254, 0.3);"></div>
        <div style="font-size: 0.75em; color: #666; font-weight: 500;">${hour}</div>
    </div>
`;
}

html += '</div>';
chartDiv.innerHTML = html;
}

function setDefaultReportDate() {
const today = new Date().toISOString().split('T')[0];
const reportDateElement = document.getElementById('reportDate');
if (reportDateElement) {
reportDateElement.value = today;
}
}

function loadDailyReport() {
const reportDateElement = document.getElementById('reportDate');
const date = reportDateElement ? reportDateElement.value : new Date().toISOString().split('T')[0];
const reportContent = document.getElementById('reportContent');

if (reportContent) {
reportContent.innerHTML = '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading daily report...</div>';
}

fetch(`/api/daily_report?date=${date}`)
.then(response => response.json())
.then(data => {
    displayDailyReport(data);
    loadRecognitionLogs(date);
    loadHistoricalData(date);
})
.catch(err => {
    if (reportContent) {
        reportContent.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Report</h3>
                <p>Failed to load daily report: ${err.message}</p>
                <p>Please try again or check your connection.</p>
            </div>
        `;
    }
    showToast(`Failed to load daily report: ${err.message}`, 'error', 'Report Error');
});
}

function loadRecognitionLogs(date) {
const logsDiv = document.getElementById('recognitionLogs');
if (logsDiv) {
logsDiv.innerHTML = '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading recognition logs...</div>';
}

fetch(`/api/recognition_logs?date=${date}`)
.then(response => response.json())
.then(data => {
    displayRecognitionLogs(data);
})
.catch(err => {
    if (logsDiv) {
        logsDiv.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Logs</h3>
                <p>Failed to load recognition logs: ${err.message}</p>
            </div>
        `;
    }
});
}

function loadHistoricalData(date) {
const historicalDiv = document.getElementById('historicalData');
if (historicalDiv) {
historicalDiv.innerHTML = '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading historical data...</div>';
}

fetch(`/api/historical_data?date=${date}`)
.then(response => response.json())
.then(data => {
    displayHistoricalData(data);
})
.catch(err => {
    if (historicalDiv) {
        historicalDiv.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Historical Data</h3>
                <p>Failed to load historical performance data: ${err.message}</p>
            </div>
        `;
    }
});
}

function generateTestData() {
showToast('Generating test data...', 'info', 'Processing');

fetch('/api/generate_test_data', { method: 'POST' })
.then(response => response.json())
.then(data => {
    if (data.success) {
        showToast('Test data generated successfully! Refreshing reports...', 'success', 'Data Generated');
        setTimeout(() => loadDailyReport(), 1000);
    } else {
        showToast(`Failed to generate test data: ${data.error}`, 'error', 'Generation Failed');
    }
})
.catch(err => {
    showToast(`Error generating test data: ${err.message}`, 'error', 'Generation Error');
});
}


function displayDailyReport(report) {
const reportContent = document.getElementById('reportContent');
if (!reportContent) return;

if (report.error) {
reportContent.innerHTML = `
    <div class="empty-state">
        <h3>Report Error</h3>
        <p>${report.error}</p>
    </div>
`;
return;
}

if (!report.summary || (report.summary.total_recognitions || 0) === 0) {
reportContent.innerHTML = `
    <div class="empty-state">
        <h3>No Activity Recorded</h3>
        <p><strong>Date:</strong> ${report.date || document.getElementById('reportDate')?.value}</p>
        <p>No face recognitions were performed on this date.</p>
        <p>Try using the "Generate Test Data" button to create sample data for testing.</p>
    </div>
`;
return;
}

let html = `
<div class="analytics-grid">
    <div class="stat-card recognition-card">
        <h4>Total Recognitions</h4>
        <div class="stat-value">${report.summary.total_recognitions}</div>
        <div class="stat-label">Face detections</div>
    </div>
    <div class="stat-card performance-card">
        <h4>Unique People</h4>
        <div class="stat-value">${report.summary.unique_people}</div>
        <div class="stat-label">Different faces</div>
    </div>
    <div class="stat-card quality-card">
        <h4>Avg Confidence</h4>
        <div class="stat-value">${(report.summary.avg_confidence * 100).toFixed(1)}%</div>
        <div class="stat-label">Recognition accuracy</div>
    </div>
    <div class="stat-card method-card">
        <h4>Avg Quality</h4>
        <div class="stat-value">${(report.summary.avg_quality * 100).toFixed(1)}%</div>
        <div class="stat-label">Image quality</div>
    </div>
</div>
`;

if (report.performance_insights && report.performance_insights.length > 0) {
html += `
    <div class="chart-container">
        <h3 class="section-title">Performance Insights</h3>
        <ul class="insights-list">
            ${report.performance_insights.map(insight => `<li>${insight}</li>`).join('')}
        </ul>
    </div>
`;
}

if (report.people_analysis && report.people_analysis.length > 0) {
html += `
    <div class="chart-container">
        <h3 class="section-title">Most Active Subjects</h3>
        <div class="people-list">
`;

report.people_analysis.slice(0, 6).forEach(person => {
    html += `
        <div class="person-card">
            <div class="person-name">${person.name}</div>
            <div class="person-stats">
                <div><strong>Recognitions:</strong> ${person.recognition_count}</div>
                <div><strong>Avg Confidence:</strong> ${(person.avg_confidence * 100).toFixed(1)}%</div>
                <div><strong>Avg Quality:</strong> ${(person.avg_quality * 100).toFixed(1)}%</div>
                <div><strong>Method:</strong> ${formatMethod(person.most_used_method)}</div>
            </div>
            <div style="margin-top: 15px;">
                <span class="confidence-level conf-${person.confidence_level}">
                    ${formatConfidenceLevel(person.confidence_level)}
                </span>
            </div>
        </div>
    `;
});

html += '</div></div>';
}

if (report.confidence_distribution) {
html += `
    <div class="chart-container">
        <h3 class="section-title">Confidence Distribution</h3>
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
`;

Object.entries(report.confidence_distribution).forEach(([level, count]) => {
    const total = Object.values(report.confidence_distribution).reduce((a, b) => a + b, 0);
    const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
    
    html += `
        <div class="confidence-level conf-${level}" style="flex: 1; min-width: 120px; text-align: center; padding: 18px;">
            <strong>${count}</strong><br>
            ${formatConfidenceLevel(level)}<br>
            <small>(${percentage}%)</small>
        </div>
    `;
});

html += '</div></div>';
}

reportContent.innerHTML = html;
}

function displayRecognitionLogs(data) {
const logsDiv = document.getElementById('recognitionLogs');
if (!logsDiv) return;

if (!data.logs || data.logs.length === 0) {
logsDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Recognition Logs</h3>
        <p>No face recognition logs found for this date.</p>
        <p>Try using the "Generate Test Data" button to create sample data.</p>
    </div>
`;
return;
}

let html = `
<div style="max-height: 500px; overflow-y: auto; border: 2px solid #e0e0e0; border-radius: 15px; padding: 20px; background: #fafafa;">
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); font-weight: 700;">
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6; border-radius: 8px 0 0 0;">Time</th>
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Person</th>
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Confidence</th>
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Quality</th>
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Method</th>
                <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6; border-radius: 0 8px 0 0;">Processing</th>
            </tr>
        </thead>
        <tbody>
`;

data.logs.forEach((log, index) => {
const time = new Date(log.timestamp).toLocaleTimeString();
const confidenceColor = log.confidence > 0.8 ? '#4caf50' : 
                      log.confidence > 0.6 ? '#8bc34a' : 
                      log.confidence > 0.4 ? '#ffc107' : '#f44336';

const rowBg = index % 2 === 0 ? 'background: white;' : 'background: #f8f9fa;';

html += `
    <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;" 
        onmouseover="this.style.background='#e3f2fd'" 
        onmouseout="this.style.background='${index % 2 === 0 ? 'white' : '#f8f9fa'}'">
        <td style="padding: 12px 15px; font-weight: 500;">${time}</td>
        <td style="padding: 12px 15px; font-weight: 700; color: #333;">${log.person_name || 'Unknown'}</td>
        <td style="padding: 12px 15px;">
            <span style="color: ${confidenceColor}; font-weight: 700;">${(log.confidence * 100).toFixed(1)}%</span>
        </td>
        <td style="padding: 12px 15px; font-weight: 600;">${(log.quality_score * 100).toFixed(1)}%</td>
        <td style="padding: 12px 15px;">
            <span class="method-badge method-${log.method_used.split('_')[0]}">${formatMethod(log.method_used)}</span>
        </td>
        <td style="padding: 12px 15px; font-weight: 500;">${(log.processing_time * 1000).toFixed(0)}ms</td>
    </tr>
`;
});

html += `
        </tbody>
    </table>
</div>
<div style="margin-top: 20px; padding: 15px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; font-size: 1em; color: #495057;">
    <strong>Summary:</strong> ${data.logs.length} total logs • 
    Avg confidence: <span style="font-weight: 700; color: #4caf50;">${(data.avg_confidence * 100).toFixed(1)}%</span> • 
    Avg quality: <span style="font-weight: 700; color: #2196f3;">${(data.avg_quality * 100).toFixed(1)}%</span>
</div>
`;

logsDiv.innerHTML = html;
}

function displayHistoricalData(data) {
const historicalDiv = document.getElementById('historicalData');
if (!historicalDiv) return;

if (!data.days || data.days.length === 0) {
historicalDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Historical Data</h3>
        <p>Historical performance data will appear here once you have multiple days of recognition activity.</p>
        <p>Continue using the system to build up historical trends and insights.</p>
    </div>
`;
return;
}

let html = `
<div class="chart-container">
    <h3 class="section-title">📈 Historical Performance Trends</h3>
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; min-width: 600px;">
            <thead>
                <tr style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); font-weight: 700;">
                    <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Date</th>
                    <th style="padding: 15px; text-align: center; border-bottom: 3px solid #dee2e6;">Recognitions</th>
                    <th style="padding: 15px; text-align: center; border-bottom: 3px solid #dee2e6;">Unique People</th>
                    <th style="padding: 15px; text-align: center; border-bottom: 3px solid #dee2e6;">Avg Confidence</th>
                    <th style="padding: 15px; text-align: center; border-bottom: 3px solid #dee2e6;">Avg Quality</th>
                </tr>
            </thead>
            <tbody>
`;

data.days.forEach((day, index) => {
const date = new Date(day.date).toLocaleDateString();
const rowBg = index % 2 === 0 ? 'background: white;' : 'background: #f8f9fa;';
const confidenceColor = day.avg_confidence > 0.8 ? '#4caf50' : 
                       day.avg_confidence > 0.6 ? '#8bc34a' : 
                       day.avg_confidence > 0.4 ? '#ffc107' : '#f44336';

html += `
    <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;"
        onmouseover="this.style.background='#e3f2fd'" 
        onmouseout="this.style.background='${index % 2 === 0 ? 'white' : '#f8f9fa'}'">
        <td style="padding: 12px 15px; font-weight: 600;">${date}</td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 700; color: #333;">${day.total_recognitions}</td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${day.unique_people}</td>
        <td style="padding: 12px 15px; text-align: center;">
            <span style="color: ${confidenceColor}; font-weight: 700;">${(day.avg_confidence * 100).toFixed(1)}%</span>
        </td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${(day.avg_quality * 100).toFixed(1)}%</td>
    </tr>
`;
});

html += `
            </tbody>
        </table>
    </div>
</div>
`;

const totalRecognitions = report.summary.total_recognitions || 0;
const uniquePeople = report.summary.unique_people || 0;
const avgConfidence = report.summary.avg_confidence || 0;
const avgQuality = report.summary.avg_quality || 0;

html += `
<div class="analytics-grid">
    <div class="stat-card recognition-card">
        <h4>Total Recognitions</h4>
        <div class="stat-value">${totalRecognitions}</div>
        <div class="stat-label">Face detections</div>
    </div>
    <div class="stat-card performance-card">
        <h4>Unique People</h4>
        <div class="stat-value">${uniquePeople}</div>
        <div class="stat-label">Different faces</div>
    </div>
    <div class="stat-card quality-card">
        <h4>Avg Confidence</h4>
        <div class="stat-value">${(avgConfidence * 100).toFixed(1)}%</div>
        <div class="stat-label">Recognition accuracy</div>
    </div>
    <div class="stat-card method-card">
        <h4>Avg Quality</h4>
        <div class="stat-value">${(avgQuality * 100).toFixed(1)}%</div>
        <div class="stat-label">Image quality</div>
    </div>
</div>
`;

historicalDiv.innerHTML = html;
}

function loadPeopleList() {
const peopleList = document.getElementById('peopleList');
if (peopleList) {
peopleList.innerHTML = '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading registered people...</div>';
}

fetch('/api/people')
.then(response => response.json())
.then(data => {
    displayPeopleList(data.people);
})
.catch(err => {
    if (peopleList) {
        peopleList.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Database</h3>
                <p>Failed to load registered people: ${err.message}</p>
            </div>
        `;
    }
    showToast(`Failed to load people list: ${err.message}`, 'error', 'Load Error');
});
}

function displayPeopleList(people) {
const peopleList = document.getElementById('peopleList');
if (!peopleList) return;

if (!people || people.length === 0) {
peopleList.innerHTML = `
    <div class="empty-state">
        <h3>No Registered Subjects</h3>
        <p>No subjects have been registered in the system yet.</p>
        <p>Use the mobile app to register subjects with multiple high-quality images for better recognition accuracy.</p>
        <p><strong>Tip:</strong> Register subjects with various lighting conditions and angles for optimal performance.</p>
    </div>
`;
return;
}

let html = `
<div class="analytics-grid" style="margin-bottom: 35px;">
    <div class="stat-card recognition-card">
        <h4>Total Subjects</h4>
        <div class="stat-value">${people.length}</div>
        <div class="stat-label">Registered</div>
    </div>
    <div class="stat-card performance-card">
        <h4>Total Photos</h4>
        <div class="stat-value">${people.reduce((sum, p) => sum + p.photo_count, 0)}</div>
        <div class="stat-label">Training Images</div>
    </div>
    <div class="stat-card quality-card">
        <h4>Avg Quality</h4>
        <div class="stat-value">${(people.reduce((sum, p) => sum + p.avg_quality, 0) / people.length * 100).toFixed(1)}%</div>
        <div class="stat-label">Overall Quality</div>
    </div>
                 <div class="stat-card method-card">
         <h4>Multi-image</h4>
         <div class="stat-value">${people.filter(p => p.registration_method === 'enhanced').length}</div>
         <div class="stat-label">Multi-image Registration</div>
     </div>
</div>

<div class="people-list">
`;

people.forEach(person => {
const registrationDate = new Date(person.created_at).toLocaleDateString();
const qualityColor = person.avg_quality > 0.7 ? '#4caf50' : 
                   person.avg_quality > 0.5 ? '#ff9800' : '#f44336';

html += `
    <div class="person-card">
        <div class="person-name">${person.name}</div>
        <div class="person-stats">
            <div><strong>Photos:</strong> <span style="color: #2196f3; font-weight: 700;">${person.photo_count}</span></div>
            <div><strong>Registered:</strong> ${registrationDate}</div>
            <div><strong>Avg Quality:</strong> 
                <span style="color: ${qualityColor}; font-weight: 700;">
                    ${(person.avg_quality * 100).toFixed(1)}%
                </span>
            </div>
            <div><strong>Best Quality:</strong> <span style="color: #4caf50; font-weight: 700;">${(person.best_quality * 100).toFixed(1)}%</span></div>
        </div>
        <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center;">
                                 <span class="method-badge method-${person.registration_method}">
                 ${person.registration_method === 'enhanced' ? 'Multi-image Registration' : 'Standard Registration'}
             </span>
            <button class="button stop" style="padding: 10px 18px; font-size: 0.85em; margin: 0;" 
                    onclick="deletePerson('${person.name}')">
                Delete
            </button>
        </div>
    </div>
`;
});

html += '</div>';
peopleList.innerHTML = html;
}

function deletePerson(name) {
const confirmed = confirm(`Are you sure you want to delete ${name} and all their face data?\n\nThis action cannot be undone.`);

if (confirmed) {
showToast(`Deleting ${name}...`, 'info', 'Processing');

fetch('/api/delete_person', {
    method: 'DELETE',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name: name })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        showToast(`${name} has been successfully deleted.`, 'success', 'Person Deleted');
        setTimeout(() => loadPeopleList(), 1000);
    } else {
        showToast(`Failed to delete ${name}: ${data.error}`, 'error', 'Deletion Failed');
    }
})
.catch(err => {
    showToast(`Error deleting ${name}: ${err.message}`, 'error', 'Deletion Error');
});
}
}

function formatMethod(method) {
const methodMap = {
'standard': 'Standard',
'weighted': 'Weighted Avg',
'temporal': 'Temporal',
'enhanced': 'Enhanced',
'outlier_removed': 'Outlier Filtered',
'weighted_average': 'Weighted Average',
'adaptive': 'Adaptive'
};

if (method.includes('_')) {
const parts = method.split('_');
return parts.map(part => methodMap[part] || part).join(' + ');
}

return methodMap[method] || method;
}

function formatConfidenceLevel(level) {
const levelMap = {
'very_high': 'Very High',
'high': 'High',
'medium': 'Medium',
'low': 'Low',
'very_low': 'Very Low'
};
return levelMap[level] || level;
}

function initializeDashboard() {
fetch('/api/health')
.then(response => {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
})
.then(data => {
    const statusEl = document.getElementById('status');
    if (statusEl) {
                         if (data.model_loaded) {
             statusEl.innerHTML = 'System Ready - Model Loaded';
             statusEl.className = 'status success';
             showToast('Face recognition system initialized successfully', 'success', 'System Ready');
         } else {
             statusEl.innerHTML = 'Model Not Loaded - Check Server Logs';
             statusEl.className = 'status warning';
             showToast('System started but model not fully loaded', 'warning', 'Partial Initialization');
         }
    }
    
    console.log('Server features:', data.features || {});
    console.log('Enhanced methods:', data.averaging_methods || {});
})
.catch(err => {
    console.error('Initial health check failed:', err);
    const statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.innerHTML = 'Cannot Connect to Server';
        statusEl.className = 'status error';
    }
    showToast('Cannot connect to face recognition server', 'error', 'Connection Failed');
});

setDefaultReportDate();
}


function startPeriodicUpdates() {
setInterval(() => {
fetch('/api/health')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.recognition_stats) {
            let stats = data.recognition_stats;
            let rate = stats.total_requests > 0 ? 
                (stats.successful_recognitions / stats.total_requests * 100).toFixed(1) : 0;
            
            const liveTab = document.getElementById('live-tab');
            if (liveTab && liveTab.classList.contains('active')) {
                if (!recognitionActive) {
                    const statusEl = document.getElementById('status');
                    if (statusEl) {
                                                                         if (!data.model_loaded) {
                     statusEl.innerHTML = 'Model Not Loaded - Basic Detection Only';
                     statusEl.className = 'status warning';
                 } else {
                     statusEl.innerHTML = 'System Ready - Model Loaded';
                     statusEl.className = 'status success';
                 }
                    }
                }
            }
            
            const analyticsTab = document.getElementById('analytics-tab');
            if (analyticsTab && analyticsTab.classList.contains('active')) {
                const elements = {
                    recognitionRate: rate + '%',
                    avgTime: (stats.avg_processing_time * 1000).toFixed(0) + 'ms',
                    totalRequests: stats.total_requests,
                    enhancedMethods: (stats.weighted_average_applied || 0) + 
                                   (stats.temporal_smoothing_applied || 0) + 
                                   (stats.outliers_removed || 0)
                };
                
                Object.entries(elements).forEach(([id, value]) => {
                    const element = document.getElementById(id);
                    if (element) element.textContent = value;
                });
            }
        }
    })
    .catch(err => {
        console.error('Periodic health check error:', err);
    });
}, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
initializeDashboard();
startPeriodicUpdates();
});
