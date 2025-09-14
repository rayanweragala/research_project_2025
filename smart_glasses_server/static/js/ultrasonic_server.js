let sensorActive = false;
let measurementInterval;
let currentDistance = 0.0;
let currentStats = {};

function showToast(message, type = "info", title = "", duration = 4000) {
  const toastContainer = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const titles = {
    success: title || "Success",
    error: title || "Error",
    warning: title || "Warning",
    info: title || "Information",
  };

  toast.innerHTML = `
        <div class="toast-header">
            <span>${titles[type]}</span>
        </div>
        <div class="toast-message">${message}</div>
    `;

  toastContainer.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 100);

  setTimeout(() => {
    if (toast.parentNode) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 400);
    }
}, duration);
}

function closeToast(button) {
  const toast = button.closest(".toast");
  toast.classList.remove("show");
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 400);
}

function switchTab(event, tabName) {
  document.querySelectorAll(".ultrasonic-tab-content").forEach((content) => {
    content.classList.remove("active");
  });

  document.querySelectorAll(".ultrasonic-tab").forEach((tab) => {
    tab.classList.remove("active");
  });

  const tabContent = document.getElementById(tabName + "-tab");
  if (tabContent) {
    tabContent.classList.add("active");
  }

  if (event && event.target) {
    event.target.classList.add("active");
  }

  switch (tabName) {
    case "analytics":
      loadAnalytics();
      break;
    case "reports":
      setDefaultReportDate();
      loadDailyReport();
      break;
  }
}

function stopSensor() {
  sensorActive = false;
  document.getElementById("status").innerHTML =
    '<span class="loading-spinner"></span>Stopping sensor...';

  if (measurementInterval) {
    clearInterval(measurementInterval);
  }

  fetch("/api/sensor/stop", { method: "POST" })
    .then(() => {
      document.getElementById("status").innerHTML = "Sensor Stopped";
      document.getElementById("status").className = "status warning";
      showToast("Sensor stopped successfully", "info", "Sensor Stopped");
    })
    .catch(() => {
      document.getElementById("status").innerHTML = "Sensor Stopped";
      document.getElementById("status").className = "status warning";
      showToast(
        "Sensor stopped (connection lost)",
        "warning",
        "Sensor Stopped"
      );
    });
}

function getCurrentDistance() {
  if (!sensorActive) return;

  fetch("/api/distance/current")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.distance !== undefined) {
        updateDistanceDisplay(data);
        displayMeasurement(data);
        updateCurrentReading(data);
      } else if (data.error) {
        displayError(data.error);
      }
    })
    .catch((err) => {
      console.error("Distance reading error:", err);
      displayError(`Connection error: ${err.message}`);
    });
}

function updateDistanceDisplay(data) {
  const distanceReading = document.getElementById("distanceReading");
  const distanceZone = document.getElementById("distanceZone");
  const qualityScore = document.getElementById("qualityScore");
  const qualityBar = document.getElementById("qualityBar");

  if (distanceReading) {
    distanceReading.textContent = data.distance.toFixed(1) + " cm";
  }

  if (distanceZone) {
    distanceZone.textContent = formatZone(data.zone);
    distanceZone.className = "distance-zone zone-" + data.zone;
  }

  if (qualityScore) {
    qualityScore.textContent = (data.quality_score * 100).toFixed(1);
  }

  if (qualityBar) {
    qualityBar.style.width = data.quality_score * 100 + "%";
  }

  currentDistance = data.distance;
}

function updateCurrentReading(data) {
  const currentReading = document.getElementById("currentReading");
  if (!currentReading) return;

  currentReading.innerHTML = `
        <div style="padding: 18px; background: linear-gradient(135deg, #e8f5e8, #f1f8e9); border-radius: 12px; margin-top: 18px; border-left: 4px solid #4caf50;">
            <div style="font-weight: 700; color: #2e7d32; font-size: 1.2em;">
                ${data.distance.toFixed(1)} cm
                <span class="distance-zone zone-${
                  data.zone
                }" style="margin-left: 10px; font-size: 0.8em; padding: 6px 12px;">
                    ${formatZone(data.zone)}
                </span>
            </div>
            <div style="font-size: 0.95em; margin-top: 10px; color: #4caf50; font-weight: 500;">
                Quality: ${(data.quality_score * 100).toFixed(1)}% • 
                Zone: ${formatZone(data.zone)} • 
                Time: ${new Date(data.timestamp).toLocaleTimeString()}
            </div>
            <div class="quality-bar">
                <div class="quality-fill" style="width: ${
                  data.quality_score * 100
                }%;"></div>
            </div>
        </div>
    `;
}

function displayMeasurement(data) {
  let measurementsDiv = document.getElementById("measurements");
  if (!measurementsDiv) return;

  let measurementClass = "zone-" + data.zone + "-log";

  let measurementHtml = `
        <div class="measurement-log ${measurementClass}">
            <div class="log-header">
                ${new Date().toLocaleTimeString()} - ${data.distance.toFixed(
    1
  )} cm
                <span class="distance-zone zone-${
                  data.zone
                }" style="margin-left: 15px; font-size: 0.9em; padding: 6px 12px;">
                    ${formatZone(data.zone)}
                </span>
            </div>
            <div class="log-details">
                Quality: ${(data.quality_score * 100).toFixed(1)}% • 
                Zone: ${formatZone(data.zone)} • 
                Timestamp: ${new Date(data.timestamp).toLocaleString()}
            </div>
            <div class="quality-bar">
                <div class="quality-fill" style="width: ${
                  data.quality_score * 100
                }%;"></div>
            </div>
        </div>
    `;

  measurementsDiv.innerHTML = measurementHtml + measurementsDiv.innerHTML;

  let measurements = measurementsDiv.children;
  while (measurements.length > 10) {
    measurementsDiv.removeChild(measurements[measurements.length - 1]);
  }
}

function displayError(errorMessage) {
  const currentReading = document.getElementById("currentReading");
  if (currentReading) {
    currentReading.innerHTML = `
            <div style="padding: 18px; background: linear-gradient(135deg, #ffebee, #fce4ec); border-radius: 12px; margin-top: 18px; border-left: 4px solid #f44336;">
                <div style="font-weight: 600; color: #c62828; font-size: 1.1em;">Error: ${errorMessage}</div>
            </div>
        `;
  }
}

function loadAnalytics() {
  fetch("/api/analytics")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      currentStats = data;
      updateAnalyticsDisplay(data);
    })
    .catch((err) => {
      console.error("Analytics error:", err);
      showToast("Failed to load analytics data", "error", "Analytics Error");

      const analyticsElements = [
        "avgDistance",
        "totalMeasurements",
        "distanceRange",
      ];
      analyticsElements.forEach((elementId) => {
        const element = document.getElementById(elementId);
        if (element) element.textContent = "0";
      });
    });
}

function updateAnalyticsDisplay(data) {
  if (data && data.stats) {
    let stats = data.stats;

    const avgDistanceEl = document.getElementById("avgDistance");
    const totalMeasurementsEl = document.getElementById("totalMeasurements");
    const distanceRangeEl = document.getElementById("distanceRange");

    if (avgDistanceEl)
      avgDistanceEl.textContent = stats.avg_distance.toFixed(1) + " cm";
    if (totalMeasurementsEl)
      totalMeasurementsEl.textContent = stats.total_measurements;

    if (distanceRangeEl) {
      if (stats.min_distance === Infinity) {
        distanceRangeEl.textContent = "0 cm";
      } else {
        distanceRangeEl.textContent = `${stats.min_distance.toFixed(
          1
        )} - ${stats.max_distance.toFixed(1)} cm`;
      }
    }
  }

  if (data && data.zone_distribution) {
    updateZoneChart(data.zone_distribution);
  }

  if (data && data.hourly_distribution) {
    updateHourlyChart(data.hourly_distribution);
  }
}

function updateZoneChart(zoneData) {
  const chartDiv = document.getElementById("zoneChart");
  const total = Object.values(zoneData).reduce((a, b) => a + b, 0);

  if (total === 0) {
    chartDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Zone Data</h3>
                <p>Zone distribution will appear here once measurements begin.</p>
            </div>
        `;
    return;
  }

  let html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">';

  Object.entries(zoneData).forEach(([zone, count]) => {
    const percentage = ((count / total) * 100).toFixed(1);
    html += `
            <div class="distance-zone zone-${zone}" style="flex: 1; min-width: 140px; text-align: center; padding: 15px;">
                ${formatZone(zone)}<br>
                <strong>${count} (${percentage}%)</strong>
            </div>
        `;
  });

  html += "</div>";
  chartDiv.innerHTML = html;
}

function updateHourlyChart(hourlyData) {
  const chartDiv = document.getElementById("hourlyChart");

  if (!hourlyData || Object.keys(hourlyData).length === 0) {
    chartDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Hourly Data</h3>
                <p>24-hour activity patterns will be shown here after collecting usage data.</p>
            </div>
        `;
    return;
  }

  const maxValue = Math.max(...Object.values(hourlyData));

  let html =
    '<div style="display: flex; align-items: end; gap: 4px; height: 180px; padding: 20px 0;">';

  for (let hour = 0; hour < 24; hour++) {
    const count = hourlyData[hour] || 0;
    const height = maxValue > 0 ? (count / maxValue) * 140 : 0;

    html += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); 
                            width: 100%; height: ${height}px; border-radius: 3px; 
                            margin-bottom: 8px; min-height: 3px;
                            ${
                              count > 0
                                ? `title='${count} measurements at ${hour}:00'`
                                : ""
                            }
                            box-shadow: 0 2px 8px rgba(79, 172, 254, 0.3);"></div>
                <div style="font-size: 0.75em; color: #666; font-weight: 500;">${hour}</div>
            </div>
        `;
  }

  html += "</div>";
  chartDiv.innerHTML = html;
}

function setDefaultReportDate() {
  const today = new Date().toISOString().split("T")[0];
  const reportDateElement = document.getElementById("reportDate");
  if (reportDateElement) {
    reportDateElement.value = today;
  }
}

function loadDailyReport() {
  const reportDateElement = document.getElementById("reportDate");
  const date = reportDateElement
    ? reportDateElement.value
    : new Date().toISOString().split("T")[0];
  const reportContent = document.getElementById("reportContent");

  if (reportContent) {
    reportContent.innerHTML =
      '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading daily report...</div>';
  }

  fetch(`/api/daily_report?date=${date}`)
    .then((response) => response.json())
    .then((data) => {
      displayDailyReport(data);
      loadMeasurementLogs(date);
    })
    .catch((err) => {
      if (reportContent) {
        reportContent.innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Report</h3>
                        <p>Failed to load daily report: ${err.message}</p>
                        <p>Please try again or check your connection.</p>
                    </div>
                `;
      }
      showToast(
        `Failed to load daily report: ${err.message}`,
        "error",
        "Report Error"
      );
    });
}

function loadMeasurementLogs(date) {
  const logsDiv = document.getElementById("measurementLogs");
  if (logsDiv) {
    logsDiv.innerHTML =
      '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading measurement logs...</div>';
  }

  fetch(`/api/measurement_logs?date=${date}`)
    .then((response) => response.json())
    .then((data) => {
      displayMeasurementLogs(data);
    })
    .catch((err) => {
      if (logsDiv) {
        logsDiv.innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Logs</h3>
                        <p>Failed to load measurement logs: ${err.message}</p>
                    </div>
                `;
      }
    });
}

function displayDailyReport(report) {
  const reportContent = document.getElementById("reportContent");
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

  if (!report.summary || report.summary.total_measurements === 0) {
    reportContent.innerHTML = `
            <div class="empty-state">
                <h3>No Activity Recorded</h3>
                <p><strong>Date:</strong> ${
                  report.date || document.getElementById("reportDate")?.value
                }</p>
                <p>No distance measurements were performed on this date.</p>
                <p>Start the sensor to begin collecting data.</p>
            </div>
        `;
    return;
  }

  let html = `
        <div class="analytics-grid">
            <div class="stat-card distance-card">
                <h4>Total Measurements</h4>
                <div class="stat-value">${report.summary.total_measurements}</div>
                <div class="stat-label">Distance readings</div>
            </div>
            <div class="stat-card measurement-card">
                <h4>Average Distance</h4>
                <div class="stat-value">${report.summary.avg_distance} cm</div>
                <div class="stat-label">Mean reading</div>
            </div>
            <div class="stat-card quality-card">
                <h4>Min Distance</h4>
                <div class="stat-value">${report.summary.min_distance} cm</div>
                <div class="stat-label">Closest detection</div>
            </div>
            <div class="stat-card range-card">
                <h4>Max Distance</h4>
                <div class="stat-value">${report.summary.max_distance} cm</div>
                <div class="stat-label">Farthest detection</div>
            </div>
        </div>
    `;

  if (report.insights && report.insights.length > 0) {
    html += `
            <div class="chart-container">
                <h3 class="section-title">Daily Insights</h3>
                <ul class="insights-list">
                    ${report.insights
                      .map((insight) => `<li>${insight}</li>`)
                      .join("")}
                </ul>
            </div>
        `;
  }

  if (report.zone_distribution) {
    html += `
            <div class="chart-container">
                <h3 class="section-title">Zone Distribution</h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
        `;

    Object.entries(report.zone_distribution).forEach(([zone, count]) => {
      const total = Object.values(report.zone_distribution).reduce(
        (a, b) => a + b,
        0
      );
      const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;

      html += `
                <div class="distance-zone zone-${zone}" style="flex: 1; min-width: 120px; text-align: center; padding: 18px;">
                    <strong>${count}</strong><br>
                    ${formatZone(zone)}<br>
                    <small>(${percentage}%)</small>
                </div>
            `;
    });

    html += "</div></div>";
  }

  if (report.hourly_activity) {
    html += `
            <div class="chart-container">
                <h3 class="section-title"> Hourly Activity</h3>
                <div style="display: flex; align-items: end; gap: 4px; height: 180px; padding: 20px 0;">
        `;

    const maxValue = Math.max(...Object.values(report.hourly_activity));

    for (let hour = 0; hour < 24; hour++) {
      const count = report.hourly_activity[hour] || 0;
      const height = maxValue > 0 ? (count / maxValue) * 140 : 0;

      html += `
                <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                    <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); 
                                width: 100%; height: ${height}px; border-radius: 3px; 
                                margin-bottom: 8px; min-height: 3px;
                                ${
                                  count > 0
                                    ? `title='${count} measurements at ${hour}:00'`
                                    : ""
                                }
                                box-shadow: 0 2px 8px rgba(79, 172, 254, 0.3);"></div>
                    <div style="font-size: 0.75em; color: #666; font-weight: 500;">${hour}</div>
                </div>
            `;
    }

    html += "</div></div>";
  }

  reportContent.innerHTML = html;
}

function displayMeasurementLogs(data) {
  const logsDiv = document.getElementById("measurementLogs");
  if (!logsDiv) return;

  if (!data.logs || data.logs.length === 0) {
    logsDiv.innerHTML = `
            <div class="empty-state">
                <h3>📝 No Measurement Logs</h3>
                <p>No distance measurement logs found for this date.</p>
                <p>Start the sensor to begin collecting data.</p>
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
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Distance</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Zone</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6; border-radius: 0 8px 0 0;">Quality</th>
                    </tr>
                </thead>
                <tbody>
    `;

  data.logs.forEach((log, index) => {
    const time = new Date(log.timestamp).toLocaleTimeString();
    const qualityColor =
      log.quality_score > 0.8
        ? "#4caf50"
        : log.quality_score > 0.6
        ? "#8bc34a"
        : log.quality_score > 0.4
        ? "#ffc107"
        : "#f44336";

    const rowBg =
      index % 2 === 0 ? "background: white;" : "background: #f8f9fa;";

    html += `
            <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;" 
                onmouseover="this.style.background='#e3f2fd'" 
                onmouseout="this.style.background='${
                  index % 2 === 0 ? "white" : "#f8f9fa"
                }'">
                <td style="padding: 12px 15px; font-weight: 500;">${time}</td>
                <td style="padding: 12px 15px; font-weight: 700; color: #333;">${
                  log.distance
                } cm</td>
                <td style="padding: 12px 15px;">
                    <span class="distance-zone zone-${
                      log.zone
                    }" style="font-size: 0.8em; padding: 4px 8px;">${formatZone(
      log.zone
    )}</span>
                </td>
                <td style="padding: 12px 15px;">
                    <span style="color: ${qualityColor}; font-weight: 700;">${(
      log.quality_score * 100
    ).toFixed(1)}%</span>
                </td>
            </tr>
        `;
  });

  html += `
                </tbody>
            </table>
        </div>
        <div style="margin-top: 20px; padding: 15px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; font-size: 1em; color: #495057;">
            <strong>Summary:</strong> ${data.logs.length} total logs • 
            Avg distance: <span style="font-weight: 700; color: #4caf50;">${
              data.avg_distance
            } cm</span> • 
            Avg quality: <span style="font-weight: 700; color: #2196f3;">${(
              data.avg_quality * 100
            ).toFixed(1)}%</span>
        </div>
    `;

  logsDiv.innerHTML = html;
}

function formatZone(zone) {
  const zoneMap = {
    very_close: "Very Close",
    close: "Close",
    medium: "Medium",
    far: "Far",
    very_far: "Very Far",
  };
  return zoneMap[zone] || zone;
}

function initializeDashboard() {
  // Auto-start the sensor when the dashboard loads
  fetch("/api/health")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      const statusEl = document.getElementById("status");
      if (statusEl) {
        if (data.sensor_active) {
          statusEl.innerHTML = "🔍 Sensor Active";
          statusEl.className = "status success";
          sensorActive = true;
          measurementInterval = setInterval(getCurrentDistance, 500);
          showToast(
            "Distance sensor is already running",
            "success",
            "Sensor Active"
          );
        } else {
          // Auto-start the sensor
          autoStartSensor();
        }
      }

      console.log("Server features:", data.features || {});
    })
    .catch((err) => {
      console.error("Initial health check failed:", err);
      const statusEl = document.getElementById("status");
      if (statusEl) {
        statusEl.innerHTML = "Cannot connect to server";
        statusEl.className = "status error";
      }
      showToast(
        "Cannot connect to distance sensor server",
        "error",
        "Connection Failed"
      );
    });

  setDefaultReportDate();
}

function autoStartSensor() {
  if (!sensorActive) {
    sensorActive = true;
    document.getElementById("status").innerHTML =
      '<span class="loading-spinner"></span>Starting sensor...';
    document.getElementById("status").className = "status warning";

    fetch("/api/sensor/start", { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          document.getElementById("status").innerHTML = "Sensor Active";
          document.getElementById("status").className = "status success";
          measurementInterval = setInterval(getCurrentDistance, 500);
          showToast("Distance sensor started", "success", "System Started");
        } else {
          document.getElementById("status").innerHTML = data.message;
          document.getElementById("status").className = "status error";
          sensorActive = false;
          showToast(data.message, "error", "Auto-start Failed");
        }
      })
      .catch((err) => {
        document.getElementById("status").innerHTML = "Connection error";
        document.getElementById("status").className = "status error";
        sensorActive = false;
        showToast(
          "Failed to auto-start sensor server",
          "error",
          "Connection Error"
        );
      });
  }
}

function startPeriodicUpdates() {
  setInterval(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
      })
      .then((data) => {
        const analyticsTab = document.getElementById("analytics-tab");
        if (analyticsTab && analyticsTab.classList.contains("active")) {
          if (data.current_distance !== undefined) {
            const elements = {
              avgDistance: data.current_distance.toFixed(1) + " cm",
              totalMeasurements: data.total_measurements,
            };

            Object.entries(elements).forEach(([id, value]) => {
              const element = document.getElementById(id);
              if (element) element.textContent = value;
            });
          }
        }
      })
      .catch((err) => {
        console.error("Periodic health check error:", err);
      });
  }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {
  initializeDashboard();
  startPeriodicUpdates();
});
