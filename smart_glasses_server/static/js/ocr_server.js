const BASE_URL = window.location.origin;
let currentExtractedText = "";
let currentDocumentData = null;

function escapeHTML(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showToast(message, type = "info", title = "", duration = 4000) {
  const toastContainer = document.getElementById("toastContainer");

  while (toastContainer.children.length >= 3) {
    const oldestToast = toastContainer.firstChild;
    oldestToast.classList.remove("show");
    setTimeout(() => oldestToast.remove(), 400);
  }

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
  // Hide all tab contents
  document.querySelectorAll(".ocr-tab-content").forEach((content) => {
    content.classList.remove("active");
  });

  document.querySelectorAll(".ocr-tab").forEach((tab) => {
    tab.classList.remove("active");
  });

  const tabContent = document.getElementById(tabName + "-tab");
  if (tabContent) {
    tabContent.classList.add("active");
  }

  if (event && event.target) {
    event.target.classList.add("active");
  }

  if (tabName === "analytics") {
    loadAnalytics();
  } else if (tabName === "history") {
    loadHistory();
  } else if (tabName === "reports") {
    setDefaultReportDate();
    loadDailyReport();
  }
}

function handleFileSelect(file) {
  const validTypes = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "application/pdf",
  ];
  if (!validTypes.includes(file.type)) {
    showToast(
      "Please select a valid image or PDF file",
      "error",
      "Invalid File Type"
    );
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showToast("File size must be less than 10MB", "error", "File Too Large");
    return;
  }

  if (file.type.startsWith("image/")) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const previewImage = document.getElementById("previewImage");
      const previewContainer = document.getElementById("previewContainer");
      if (previewImage && previewContainer) {
        previewImage.src = e.target.result;
        previewContainer.style.display = "block";
      }
    };
    reader.readAsDataURL(file);
  } else {
    const previewContainer = document.getElementById("previewContainer");
    if (previewContainer) {
      previewContainer.style.display = "none";
    }
  }

  currentDocumentData = file;
  const processBtn = document.getElementById("processBtn");
  if (processBtn) {
    processBtn.disabled = false;
  }
  updateStatus("Document loaded. Ready to process.", "success");
  showToast(
    `${escapeHTML(file.name)} loaded successfully`,
    "success",
    "File Loaded"
  );
}

function processDocument() {
  if (!currentDocumentData) {
    showToast("Please select a document first", "warning", "No Document");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    const base64Data = e.target.result.split(",")[1];

    updateStatus("Processing document...", "info");
    document.getElementById("processingIndicator").style.display = "block";
    processBtn.disabled = true;

    fetch(`${BASE_URL}/api/ocr/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64Data }),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        document.getElementById("processingIndicator").style.display = "none";
        processBtn.disabled = false;

        if (data.success) {
          displayResults(data);
          updateStatus("Document processed successfully!", "success");
          showToast(
            "Document processed successfully",
            "success",
            "Processing Complete"
          );
        } else {
          updateStatus(
            `Processing failed: ${escapeHTML(data.error || "Unknown error")}`,
            "error"
          );
          showToast(
            escapeHTML(data.error || "Unknown error"),
            "error",
            "Processing Failed"
          );
        }
      })
      .catch((err) => {
        document.getElementById("processingIndicator").style.display = "none";
        processBtn.disabled = false;
        updateStatus(`Connection error: ${err.message}`, "error");
        showToast(
          `Failed to connect to OCR server: ${err.message}`,
          "error",
          "Connection Error"
        );
      });
  };
  reader.readAsDataURL(currentDocumentData);
}

function displayResults(data) {
  const documentInfo = document.getElementById("documentInfo");
  const extractedText = document.getElementById("extractedText");
  const speakBtn = document.getElementById("speakBtn");

  document.getElementById("docType").textContent = escapeHTML(
    data.document_type || "Unknown"
  );
  document.getElementById("classificationConf").textContent = (
    (data.classification_confidence || 0) * 100
  ).toFixed(1);
  document.getElementById("ocrConf").textContent = (
    (data.ocr_confidence || 0) * 100
  ).toFixed(1);
  document.getElementById("qualityScore").textContent = (
    (data.quality_score || 0) * 100
  ).toFixed(1);
  document.getElementById("procTime").textContent = (
    (data.processing_time || 0) * 1000
  ).toFixed(0);

  const confidenceBar = document.getElementById("confidenceBar");
  confidenceBar.style.width = `${(data.ocr_confidence || 0) * 100}%`;

  documentInfo.style.display = "block";

  currentExtractedText = data.extracted_text || "";
  extractedText.textContent = escapeHTML(
    currentExtractedText || "No text was extracted from the document."
  );
  extractedText.className =
    "text-output" +
    (currentExtractedText.match(/[\u0D80-\u0DFF]/) ? " sinhala" : "");

  speakBtn.disabled = !currentExtractedText;
}

function speakText() {
  if (!currentExtractedText) {
    showToast("No text to speak", "warning", "No Text");
    return;
  }

  updateStatus("Converting text to speech...", "info");

  fetch(`${BASE_URL}/api/ocr/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: currentExtractedText }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        updateStatus("Text-to-speech completed", "success");
        showToast("Text spoken successfully", "success", "TTS Complete");
      } else {
        updateStatus("Text-to-speech failed", "error");
        showToast(
          escapeHTML(data.error || "Unknown error"),
          "error",
          "TTS Failed"
        );
      }
    })
    .catch((err) => {
      updateStatus(`TTS error: ${err.message}`, "error");
      showToast(
        `Text-to-speech connection failed: ${err.message}`,
        "error",
        "TTS Error"
      );
    });
}

function clearResults() {
  currentExtractedText = "";
  currentDocumentData = null;

  document.getElementById("extractedText").textContent =
    "Extracted text will appear here after processing...";
  document.getElementById("documentInfo").style.display = "none";
  document.getElementById("previewContainer").style.display = "none";
  document.getElementById("fileInput").value = "";

  const processBtn = document.getElementById("processBtn");
  const speakBtn = document.getElementById("speakBtn");

  if (processBtn) processBtn.disabled = true;
  if (speakBtn) speakBtn.disabled = true;

  updateStatus("Ready for document processing", "info");
  showToast("Results cleared", "info", "Cleared");
}

function updateStatus(message, type) {
  const status = document.getElementById("status");
  status.textContent = escapeHTML(message);
  status.className = `status ${type}`;
}

function loadAnalytics() {
  fetch(`${BASE_URL}/api/ocr/stats`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        updateAnalyticsDisplay(data.stats);
      } else {
        showToast(
          escapeHTML(data.error || "Failed to load analytics"),
          "error",
          "Analytics Error"
        );
      }
    })
    .catch((err) => {
      showToast(
        `Failed to load analytics: ${err.message}`,
        "error",
        "Analytics Error"
      );
    });
}

function updateAnalyticsDisplay(stats) {
  const totalDocs = stats.total_documents || 0;
  const successful = stats.successful_ocr || 0;
  const successRate =
    totalDocs > 0 ? ((successful / totalDocs) * 100).toFixed(1) : 0;
  const identificationRate =
    totalDocs > 0
      ? (((totalDocs - stats.errors || 0) / totalDocs) * 100).toFixed(1)
      : 0;
  const avgTime = (stats.avg_processing_time || 0) * 1000;

  document.getElementById("totalDocs").textContent = totalDocs;
  document.getElementById("successRate").textContent = successRate + "%";
  document.getElementById("identificationRate").textContent =
    identificationRate + "%";
  document.getElementById("avgTime").textContent = avgTime.toFixed(0) + "ms";

  updateDocTypeChart(stats.document_types || {});
  updatePerformanceChart(stats);
  updateQualityChart(stats);
}

function updateDocTypeChart(docTypes) {
  const chartDiv = document.getElementById("docTypeChart");
  const total = Object.values(docTypes).reduce((a, b) => a + b, 0);

  if (total === 0) {
    chartDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Document Types Available</h3>
                <p>Document type distribution will appear here after processing documents.</p>
            </div>
        `;
    return;
  }

  chartDiv.innerHTML = '<canvas id="docTypeCanvas"></canvas>';
  const ctx = document.getElementById("docTypeCanvas").getContext("2d");

  new Chart(ctx, {
    type: "pie",
    data: {
      labels: Object.keys(docTypes),
      datasets: [
        {
          data: Object.values(docTypes),
          backgroundColor: [
            "#34495e",
            "#2ecc71",
            "#3498db",
            "#9b59b6",
            "#e74c3c",
          ],
          borderColor: "#ffffff",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        title: { display: true, text: "Document Type Distribution" },
      },
    },
  });
}

function updatePerformanceChart(stats) {
  const chartDiv = document.getElementById("performanceChart");
  const processingTimes = stats.processing_times || [];

  if (processingTimes.length === 0) {
    chartDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Performance Data Available</h3>
                <p>Processing performance metrics will be displayed here after document processing.</p>
            </div>
        `;
    return;
  }

  chartDiv.innerHTML = '<canvas id="performanceCanvas"></canvas>';
  const ctx = document.getElementById("performanceCanvas").getContext("2d");

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Average Processing", "Error Rate", "Success Rate"],
      datasets: [
        {
          label: "Performance Metrics",
          data: [
            (stats.avg_processing_time || 0) * 1000,
            stats.total_documents > 0
              ? (((stats.errors || 0) / stats.total_documents) * 100).toFixed(1)
              : 0,
            stats.total_documents > 0
              ? (
                  ((stats.total_documents - (stats.errors || 0)) /
                    stats.total_documents) *
                  100
                ).toFixed(1)
              : 0,
          ],
          backgroundColor: ["#34495e", "#e74c3c", "#2ecc71"],
          borderColor: "#ffffff",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true },
      },
      plugins: {
        legend: { display: false },
        title: { display: true, text: "Processing Performance" },
      },
    },
  });
}

function updateQualityChart(stats) {
  const chartDiv = document.getElementById("qualityChart");

  chartDiv.innerHTML = '<canvas id="qualityCanvas"></canvas>';
  const ctx = document.getElementById("qualityCanvas").getContext("2d");

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Avg Quality Score", "Avg Confidence"],
      datasets: [
        {
          label: "Quality Metrics",
          data: [
            (stats.avg_quality || 0) * 100,
            (stats.avg_confidence || 0) * 100,
          ],
          backgroundColor: ["#9b59b6", "#3498db"],
          borderColor: "#ffffff",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, max: 100 },
      },
      plugins: {
        legend: { display: false },
        title: { display: true, text: "Quality Analysis" },
      },
    },
  });
}

function loadHistory() {
  fetch(`${BASE_URL}/api/ocr/results?limit=20`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        displayHistory(data.results);
      } else {
        throw new Error(data.error || "Unknown error");
      }
    })
    .catch((err) => {
      document.getElementById("recentDocuments").innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading History</h3>
                    <p>Failed to load document history: ${escapeHTML(
                      err.message
                    )}</p>
                </div>
            `;
    });
}

function displayHistory(results) {
  const historyDiv = document.getElementById("recentDocuments");

  if (!results || results.length === 0) {
    historyDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Document History</h3>
                <p>Processed documents will appear here after you start using the OCR system.</p>
            </div>
        `;
    return;
  }

  let html = "";
  results.forEach((result) => {
    const date = new Date(result.timestamp).toLocaleString();
    const preview = escapeHTML((result.extracted_text || "").substring(0, 150));
    const classificationConfidence = result.classification_confidence
      ? (result.classification_confidence * 100).toFixed(1)
      : "N/A";
    const quality = result.image_quality
      ? (result.image_quality * 100).toFixed(1)
      : "N/A";

    html += `
            <div class="document-card">
                <div class="document-header">
                    <div>
                        <div class="document-type">${escapeHTML(
                          result.document_type || "Unknown"
                        )}</div>
                        <div class="document-time">${date}</div>
                    </div>
                    <div style="text-align: right; font-size: 0.9em; color: #666;">
                        <div>Classification: <strong>${classificationConfidence}%</strong></div>
                        <div>Quality: <strong>${quality}%</strong></div>
                    </div>
                </div>
                <div class="document-preview">${preview}</div>
            </div>
        `;
  });

  historyDiv.innerHTML = html;
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

  fetch(`${BASE_URL}/api/ocr/daily_report?date=${date}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        reportContent.innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Report</h3>
                        <p>${escapeHTML(data.error)}</p>
                    </div>
                `;
        return;
      }

      displayDailyReport(data);
    })
    .catch((err) => {
      reportContent.innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading Report</h3>
                    <p>Failed to load daily report: ${escapeHTML(
                      err.message
                    )}</p>
                </div>
            `;
    });

  loadProcessingLogs(date);
  loadHistoricalData();
}

function displayDailyReport(data) {
  const reportContent = document.getElementById("reportContent");
  if (!reportContent) return;

  const summary = data.summary || {};
  const docTypes = data.document_types || {};
  const insights = data.insights || [];

  let docTypesHtml = "";
  if (Object.keys(docTypes).length > 0) {
    docTypesHtml =
      '<div style="margin: 20px 0;"><h4>Document Type Distribution:</h4><div style="display: flex; flex-wrap: wrap; gap: 10px;">';
    for (const [type, count] of Object.entries(docTypes)) {
      docTypesHtml += `<span class="document-type">${escapeHTML(
        type
      )}: ${count}</span>`;
    }
    docTypesHtml += "</div></div>";
  } else {
    docTypesHtml = "<p>No document type data available.</p>";
  }

  let insightsHtml = "";
  if (insights.length > 0) {
    insightsHtml =
      '<div class="chart-container"><h3 class="section-title">Insights</h3><ul class="insights-list">';
    insights.forEach((insight) => {
      insightsHtml += `<li>${escapeHTML(insight)}</li>`;
    });
    insightsHtml += "</ul></div>";
  }

  reportContent.innerHTML = `
        <div class="analytics-grid">
            <div class="stat-card documents-card">
                <h4>Documents Processed</h4>
                <div class="stat-value">${summary.total_documents || 0}</div>
                <div class="stat-label">Today's Processing</div>
            </div>
            <div class="stat-card success-card">
                <h4>OCR Success Rate</h4>
                <div class="stat-value">${
                  summary.ocr_success_rate
                    ? summary.ocr_success_rate.toFixed(1)
                    : 0
                }%</div>
                <div class="stat-label">Text Extraction</div>
            </div>
            <div class="stat-card identification-card">
                <h4>Identification Rate</h4>
                <div class="stat-value">${
                  summary.identification_success_rate
                    ? summary.identification_success_rate.toFixed(1)
                    : 0
                }%</div>
                <div class="stat-label">Type Classification</div>
            </div>
            <div class="stat-card time-card">
                <h4>Avg Time</h4>
                <div class="stat-value">${
                  summary.avg_processing_time
                    ? (summary.avg_processing_time * 1000).toFixed(0)
                    : 0
                }ms</div>
                <div class="stat-label">Processing Time</div>
            </div>
        </div>
        
        ${docTypesHtml}
        
        <div class="chart-container">
            <h3 class="section-title">Quality Metrics</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>Average Quality Score</h4>
                    <div class="stat-value" style="font-size: 2.5em;">${
                      summary.avg_quality
                        ? (summary.avg_quality * 100).toFixed(1)
                        : 0
                    }%</div>
                </div>
                <div>
                    <h4>Average Confidence</h4>
                    <div class="stat-value" style="font-size: 2.5em;">${
                      summary.avg_confidence
                        ? (summary.avg_confidence * 100).toFixed(1)
                        : 0
                    }%</div>
                </div>
            </div>
        </div>
        
        ${insightsHtml}
    `;
}

function loadProcessingLogs(date) {
  const logsDiv = document.getElementById("processingLogs");
  if (!logsDiv) return;

  logsDiv.innerHTML =
    '<div style="text-align: center; padding: 20px;"><span class="loading-spinner"></span>Loading processing logs...</div>';

  fetch(`${BASE_URL}/api/ocr/processing_logs?date=${date}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        logsDiv.innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Logs</h3>
                        <p>${escapeHTML(data.error)}</p>
                    </div>
                `;
        return;
      }

      displayProcessingLogs(data);
    })
    .catch((err) => {
      logsDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading Logs</h3>
                    <p>Failed to load processing logs: ${escapeHTML(
                      err.message
                    )}</p>
                </div>
            `;
    });
}

function displayProcessingLogs(data) {
  const logsDiv = document.getElementById("processingLogs");
  if (!logsDiv) return;

  const logs = data.logs || [];

  if (logs.length === 0) {
    logsDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Logs Available</h3>
                <p>No processing logs found for the selected date.</p>
            </div>
        `;
    return;
  }

  let logsHtml = `
        <div style="max-height: 400px; overflow-y: auto;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); font-weight: 700;">
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Time</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Action</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Document Type</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Status</th>
                        <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Processing Time</th>
                    </tr>
                </thead>
                <tbody>
    `;

  logs.forEach((log) => {
    const time = new Date(log.timestamp).toLocaleTimeString();
    const statusClass = log.success ? "status-success" : "status-failed";
    const statusText = escapeHTML(
      log.status || (log.success ? "Success" : "Failed")
    );
    const action = escapeHTML(log.action || "N/A");
    const documentType = escapeHTML(log.document_type || "N/A");
    const processingTime = log.processing_time
      ? (log.processing_time * 1000).toFixed(0) + "ms"
      : "N/A";

    logsHtml += `
            <tr style="background: white; border-bottom: 1px solid #f0f0f0;">
                <td style="padding: 12px 15px;">${time}</td>
                <td style="padding: 12px 15px;">${action}</td>
                <td style="padding: 12px 15px;">${documentType}</td>
                <td style="padding: 12px 15px;">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </td>
                <td style="padding: 12px 15px;">${processingTime}</td>
            </tr>
        `;
  });

  logsHtml += `
                </tbody>
            </table>
        </div>
        <div style="margin-top: 15px; font-style: italic; color: #666;">
            Showing ${logs.length} log entries
        </div>
    `;

  logsDiv.innerHTML = logsHtml;
}

function loadHistoricalData() {
  const historicalDiv = document.getElementById("historicalData");
  if (!historicalDiv) return;

  historicalDiv.innerHTML =
    '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading historical data...</div>';

  fetch(`${BASE_URL}/api/ocr/historical_data?days=7`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        historicalDiv.innerHTML = `
                    <div class="empty-state">
                        <h3>Error Loading Historical Data</h3>
                        <p>${escapeHTML(data.error)}</p>
                    </div>
                `;
        return;
      }

      displayHistoricalData(data);
    })
    .catch((err) => {
      historicalDiv.innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading Historical Data</h3>
                    <p>Failed to load historical data: ${escapeHTML(
                      err.message
                    )}</p>
                </div>
            `;
    });
}

function displayHistoricalData(data) {
  const historicalDiv = document.getElementById("historicalData");
  if (!historicalDiv) return;

  const days = data.days || [];

  if (days.length === 0) {
    historicalDiv.innerHTML = `
            <div class="empty-state">
                <h3>No Historical Data</h3>
                <p>No historical data available for the last 7 days.</p>
            </div>
        `;
    return;
  }

  let historicalHtml = `
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); font-weight: 700;">
                        <th style="padding: 15px; text-align: left;">Date</th>
                        <th style="padding: 15px; text-align: center;">Documents</th>
                        <th style="padding: 15px; text-align: center;">Success Rate</th>
                        <th style="padding: 15px; text-align: center;">Avg Quality</th>
                        <th style="padding: 15px; text-align: center;">Avg Time</th>
                    </tr>
                </thead>
                <tbody>
    `;

  days.forEach((day) => {
    historicalHtml += `
            <tr style="background: white; border-bottom: 1px solid #f0f0f0;">
                <td style="padding: 12px 15px; font-weight: 600;">${escapeHTML(
                  day.date
                )}</td>
                <td style="padding: 12px 15px; text-align: center; font-weight: 700;">${
                  day.total_documents || 0
                }</td>
                <td style="padding: 12px 15px; text-align: center; color: #4caf50; font-weight: 700;">${
                  day.ocr_success_rate
                    ? (day.ocr_success_rate * 100).toFixed(1) + "%"
                    : "N/A"
                }</td>
                <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${
                  day.avg_quality
                    ? (day.avg_quality * 100).toFixed(1) + "%"
                    : "N/A"
                }</td>
                <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${
                  day.avg_processing_time
                    ? (day.avg_processing_time * 1000).toFixed(0) + "ms"
                    : "N/A"
                }</td>
            </tr>
        `;
  });

  historicalHtml += `
                </tbody>
            </table>
        </div>
    `;

  historicalDiv.innerHTML = historicalHtml;
}

function generateTestData() {
  showToast("Generating test data...", "info", "Processing");

  fetch(`${BASE_URL}/api/ocr/generate_test_data`, {
    method: "POST",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        showToast(
          "Test data generated successfully!",
          "success",
          "Data Generated"
        );
        loadDailyReport();
        if (
          document.getElementById("analytics-tab").classList.contains("active")
        ) {
          loadAnalytics();
        }
      } else {
        showToast(
          `Failed to generate test data: ${escapeHTML(
            data.error || "Unknown error"
          )}`,
          "error",
          "Error"
        );
      }
    })
    .catch((err) => {
      showToast(
        `Failed to generate test data: ${err.message}`,
        "error",
        "Error"
      );
    });
}

let cameraInterval = null;
let cameraActive = false;

function startCamera() {
  const startBtn = document.getElementById("startCameraBtn");
  const stopBtn = document.getElementById("stopCameraBtn");
  const captureBtn = document.getElementById("captureBtn");

  startBtn.disabled = true;
  startBtn.textContent = "Starting...";

  fetch(`${BASE_URL}/api/camera/start`, {
    method: "POST",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        cameraActive = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        captureBtn.disabled = false;
        startBtn.textContent = "Start Camera";

        showToast("Camera started successfully", "success", "Camera Active");
        startCameraFeed();
      } else {
        throw new Error(data.message || "Failed to start camera");
      }
    })
    .catch((err) => {
      startBtn.disabled = false;
      startBtn.textContent = "Start Camera";
      showToast(
        `Failed to start camera: ${err.message}`,
        "error",
        "Camera Error"
      );
    });
}

function stopCamera() {
  const startBtn = document.getElementById("startCameraBtn");
  const stopBtn = document.getElementById("stopCameraBtn");
  const captureBtn = document.getElementById("captureBtn");

  cameraActive = false;
  if (cameraInterval) {
    clearInterval(cameraInterval);
    cameraInterval = null;
  }

  fetch(`${BASE_URL}/api/camera/stop`, {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      startBtn.disabled = false;
      stopBtn.disabled = true;
      captureBtn.disabled = true;

      document.getElementById("cameraPreview").style.display = "none";
      document.getElementById("cameraPlaceholder").style.display = "block";

      showToast("Camera stopped", "info", "Camera Inactive");
    })
    .catch((err) => {
      showToast(
        `Error stopping camera: ${err.message}`,
        "warning",
        "Camera Warning"
      );
    });
}


function startCameraFeed() {
  const preview = document.getElementById("cameraPreview");
  const placeholder = document.getElementById("cameraPlaceholder");

  cameraInterval = setInterval(() => {
    if (!cameraActive) {
      clearInterval(cameraInterval);
      return;
    }

    fetch(`${BASE_URL}/api/camera/frame?include_image=true&image_quality=75`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (data.success && data.image) {
          preview.src = `data:image/jpeg;base64,${data.image}`;
          preview.style.display = "block";
          placeholder.style.display = "none";
        } else if (data.error) {
          console.warn("Camera frame error:", data.error);
        }
      })
      .catch((err) => {
        console.warn("Camera feed error:", err);
      });
  }, 200);
}


function captureFromCamera() {
  fetch(`${BASE_URL}/api/camera/frame?include_image=true&image_quality=85`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success && data.image) {
        const img = document.getElementById("cameraPreview");
        if (img.src) {
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");

          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          ctx.drawImage(img, 0, 0);

          canvas.toBlob(
            (blob) => {
              currentDocumentData = new File([blob], "camera-capture.jpg", {
                type: "image/jpeg",
              });

              const previewImg = document.getElementById("previewImage");
              const previewContainer = document.getElementById("previewContainer");
              previewImg.src = img.src;
              previewContainer.style.display = "block";

              document.getElementById("processBtn").disabled = false;
              updateStatus("Camera frame captured. Ready to process.", "success");
              showToast("Frame captured successfully", "success", "Capture Complete");
            },
            "image/jpeg",
            0.85
          );
        }
      } else {
        showToast("Failed to capture frame", "error", "Capture Failed");
      }
    })
    .catch((err) => {
      showToast(`Capture error: ${err.message}`, "error", "Capture Error");
    });
}

function initializeDashboard() {
  fetch(`${BASE_URL}/api/ocr/health`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      const statusEl = document.getElementById("status");
      if (statusEl) {
        if (data.model_loaded && data.ocr_ready) {
          statusEl.innerHTML = "OCR System Ready - All models loaded";
          statusEl.className = "status success";
          showToast("OCR system started", "success", "System Ready");
        } else {
          statusEl.innerHTML = "OCR System ready - All models loaded";
          statusEl.className = "status success";
          showToast("OCR system started", "warning", "System Ready");
        }
      }
    })
    .catch((err) => {
      const statusEl = document.getElementById("status");
      if (statusEl) {
        statusEl.innerHTML = "Cannot connect to OCR server";
        statusEl.className = "status error";
      }
      showToast(
        `Cannot connect to OCR server: ${err.message}`,
        "error",
        "Connection Failed"
      );
    });

  setDefaultReportDate();
}

document.addEventListener("DOMContentLoaded", function () {
  const uploadArea = document.getElementById("uploadArea");
  const fileInput = document.getElementById("fileInput");
  const previewContainer = document.getElementById("previewContainer");
  const previewImage = document.getElementById("previewImage");
  const processBtn = document.getElementById("processBtn");

  if (uploadArea && fileInput) {
    uploadArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadArea.classList.add("dragover");
    });

    uploadArea.addEventListener("dragleave", () => {
      uploadArea.classList.remove("dragover");
    });

    uploadArea.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadArea.classList.remove("dragover");
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    });

    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
      }
    });
  }

  initializeDashboard();
});

window.addEventListener("beforeunload", function () {
  if (cameraActive) {
    stopCamera();
  }
});
