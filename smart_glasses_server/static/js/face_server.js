let recognitionActive = false;
let recognitionInterval;
let currentStats = {};
let capturedImages = [];
let previewInterval;
let socket = null;
let useWebSocket = true; 
let wsReconnectAttempts = 0;
let wsMaxReconnectAttempts = 3;

let streamConfig = {
  frameRate: 25, 
  quality: 70,  
  lastFrameTime: 0,
  avgLatency: 0,
  latencyCount: 0,
  drawBoxes: true
};

function openAddPersonModal() {
  const modal = document.getElementById("addPersonModal");
  modal.classList.add("show");
  document.getElementById("personName").value = "";
  capturedImages = [];
  updateCapturedImagesDisplay();
  startPreview();
}

function closeAddPersonModal() {
  const modal = document.getElementById("addPersonModal");
  modal.classList.remove("show");
  stopPreview();
  capturedImages = [];
}

function startPreview() {
  const previewFrame = document.getElementById("previewFrame");
  previewInterval = setInterval(() => {
    fetch("/api/camera/frame_add_friend")
      .then((response) => response.json())
      .then((data) => {
        if (data.success && data.frame_data.image) {
          previewFrame.innerHTML = `<img src="data:image/jpeg;base64,${data.frame_data.image}" alt="Preview">`;
        }
      })
      .catch((err) => {
        console.error("Preview error:", err);
      });
  }, 500);
}

function stopPreview() {
  if (previewInterval) {
    clearInterval(previewInterval);
    previewInterval = null;
  }
}

function captureImage() {
  fetch("/api/camera/frame_add_friend")
    .then((response) => response.json())
    .then((data) => {
      if (data.success && data.frame_data.image) {
        let base64Data = data.frame_data.image;

        if (base64Data.startsWith("data:image/")) {
          base64Data = base64Data.split(",")[1];
        }

        if (!isValidBase64(base64Data)) {
          showToast("Invalid image format received", "error");
          return;
        }

        base64Data = addBase64Padding(base64Data);

        capturedImages.push(base64Data);
        updateCapturedImagesDisplay();
        showToast(
          `Image ${capturedImages.length} captured successfully!`,
          "success"
        );
      } else {
        showToast("Failed to capture image", "error");
      }
    })
    .catch((err) => {
      showToast("Error capturing image", "error");
      console.error("Capture error:", err);
    });
}

function isValidBase64(str) {
  try {
    const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
    if (!base64Regex.test(str)) {
      return false;
    }

    atob(str);
    return true;
  } catch (e) {
    return false;
  }
}

function addBase64Padding(base64) {
  while (base64.length % 4 !== 0) {
    base64 += "=";
  }
  return base64;
}

function removeCapturedImage(index) {
  capturedImages.splice(index, 1);
  updateCapturedImagesDisplay();
}

function updateCapturedImagesDisplay() {
  const container = document.getElementById("capturedImages");
  container.innerHTML = "";

  capturedImages.forEach((image, index) => {
    const imageDiv = document.createElement("div");
    imageDiv.className = "captured-image";
    imageDiv.innerHTML = `
          <img src="data:image/jpeg;base64,${image}" alt="Captured ${index + 1
      }">
          <button class="remove-btn" onclick="removeCapturedImage(${index})">&times;</button>
      `;
    container.appendChild(imageDiv);
  });

  const submitBtn = document.getElementById("submitBtn");
  submitBtn.disabled = capturedImages.length === 0;
}

function showToast(message, type = "info", title = "", duration = 4000) {
  const toastContainer = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  const icons = {
    success: "",
    error: "",
    warning: "",
    info: "",
  };

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
      toast.classList.remove("show");
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
  document.querySelectorAll(".face-tab-content").forEach((content) => {
    content.classList.remove("active");
  });
  document.querySelectorAll(".face-tab").forEach((tab) => {
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
    case "people":
      loadPeopleList();
      break;
    case "live":
      break;
  }
}

function startRecognition() {
  if (!recognitionActive) {
    recognitionActive = true;
    document.getElementById("status").innerHTML =
      '<span class="loading-spinner"></span>Initializing camera system...';
    document.getElementById("status").className = "status warning";

    fetch("/api/camera/start", { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          document.getElementById("status").innerHTML =
            "Recognition System Active";
          document.getElementById("status").className = "status success";
          
          if (useWebSocket) {
            initWebSocketStream();
          } else {
            initHTTPStream();
          }

          showToast(
            "Camera system initialized successfully",
            "success",
            "System Started"
          );
        } else {
          document.getElementById("status").innerHTML =
            "Error: " + data.message;
          document.getElementById("status").className = "status error";
          recognitionActive = false;
          showToast(data.message, "error", "Initialization Failed");
        }
      })
      .catch((err) => {
        document.getElementById("status").innerHTML = "Connection Error";
        document.getElementById("status").className = "status error";
        recognitionActive = false;
        showToast(
          "Failed to connect to camera server",
          "error",
          "Connection Error"
        );
      });
  }
}

function initWebSocketStream() {
  try {
    if (typeof io === 'undefined') {
      console.log("Socket.IO library not loaded, falling back to HTTP");
      useWebSocket = false;
      initHTTPStream();
      return;
    }
    
    console.log("Initializing WebSocket stream...");
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = window.location.port ? `:${window.location.port}` : '';
    const wsUrl = `${window.location.protocol}//${host}${port}`;
    
    socket = io(wsUrl, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: wsMaxReconnectAttempts,
      transports: ['websocket', 'polling'],
      upgrade: true,
      path: '/socket.io/',
      timeout: 20000,
      query: {
        transport: 'websocket'
      }
    });
    
    socket.on('connect', function() {
      console.log('✓ WebSocket connected:', socket.id);
      wsReconnectAttempts = 0;
      
      const statusEl = document.getElementById("status");
      if (statusEl) {
        statusEl.innerHTML = "Recognition System Active (WebSocket)";
        statusEl.className = "status success";
      }
      
      showToast("Connected via WebSocket (faster)", "success", "Stream Mode");
    });
    
    socket.on('connected', function(data) {
      console.log('✓ Server responded:', data);
    });
    
    socket.on('frame_update', function(data) {
      if (!recognitionActive) return;
      
      const cameraFeed = document.getElementById("cameraFeed");
      if (cameraFeed && data.image) {
        cameraFeed.src = "data:image/jpeg;base64," + data.image;
      }
      
      displayResult(data);
      updateCurrentResult(data);
    });
    
    socket.on('disconnect', function(reason) {
      console.log('WebSocket disconnected. Reason:', reason);
      
      if (reason === 'io server disconnect') {
        console.log("Server disconnected, attempting reconnect...");
        socket.connect();
      } else if (recognitionActive && wsReconnectAttempts < wsMaxReconnectAttempts) {
        wsReconnectAttempts++;
        showToast(
          `WebSocket disconnected. Reconnecting... (${wsReconnectAttempts}/${wsMaxReconnectAttempts})`,
          "warning",
          "Connection"
        );
      } else if (recognitionActive) {
        console.log("Max reconnection attempts reached, falling back to HTTP");
        useWebSocket = false;
        if (socket) {
          socket.disconnect();
          socket = null;
        }
        initHTTPStream();
        showToast("Switched to HTTP mode (polling)", "info", "Stream Mode");
      }
    });
    
    socket.on('connect_error', function(error) {
      console.error('✗ WebSocket connection error:', error);
      wsReconnectAttempts++;
      
      if (wsReconnectAttempts >= wsMaxReconnectAttempts) {
        console.log("WebSocket failed after max retries, using HTTP fallback");
        useWebSocket = false;
        if (socket) {
          socket.disconnect();
          socket = null;
        }
        initHTTPStream();
        showToast("Using HTTP mode (slower)", "warning", "Stream Mode");
      }
    });
    
    socket.on('error', function(error) {
      console.error('✗ WebSocket error event:', error);
      if (recognitionActive) {
        showToast("WebSocket error, retrying...", "warning", "Connection");
      }
    });
    
    socket.on('connect_timeout', function() {
      console.error('✗ WebSocket connection timeout');
      wsReconnectAttempts++;
      if (wsReconnectAttempts >= wsMaxReconnectAttempts) {
        useWebSocket = false;
        if (socket) {
          socket.disconnect();
          socket = null;
        }
        initHTTPStream();
      }
    });
    
  } catch (error) {
    console.error("✗ WebSocket initialization error:", error);
    useWebSocket = false;
    if (socket) {
      try {
        socket.disconnect();
      } catch (e) {}
      socket = null;
    }
    initHTTPStream();
    showToast("WebSocket unavailable, using HTTP", "info", "Stream Mode");
  }
}


function initHTTPStream() {
  streamConfig.frameRate = 2;  
  recognitionInterval = setInterval(getServerFrame, 1000 / streamConfig.frameRate);
  
  const statusEl = document.getElementById("status");
  if (statusEl) {
    statusEl.innerHTML = "Recognition System Active (HTTP)";
  }
}

function stopRecognition() {
  recognitionActive = false;
  document.getElementById("status").innerHTML =
    '<span class="loading-spinner"></span>Terminating camera system...';

  if (socket) {
    socket.disconnect();
    socket = null;
  }
  
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }

  fetch("/api/camera/stop", { method: "POST" })
    .then(() => {
      document.getElementById("status").innerHTML =
        "Recognition System Terminated";
      document.getElementById("status").className = "status warning";
      showToast(
        "Recognition system terminated successfully",
        "info",
        "System Stopped"
      );
    })
    .catch(() => {
      document.getElementById("status").innerHTML =
        "Recognition System Terminated";
      document.getElementById("status").className = "status warning";
    });
}

function getServerFrame() {
  if (!recognitionActive) return;

  const requestStart = Date.now();
  const url = `/api/camera/frame?quality=${streamConfig.quality}&draw_boxes=${streamConfig.drawBoxes}`;

  fetch(url)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then((data) => {
      const requestEnd = Date.now();
      const latency = requestEnd - requestStart;
      
      streamConfig.latencyCount++;
      streamConfig.avgLatency = 
        (streamConfig.avgLatency * (streamConfig.latencyCount - 1) + latency) / streamConfig.latencyCount;
      
      if (streamConfig.latencyCount % 10 === 0) {  
        if (streamConfig.avgLatency > 1500) {  
          streamConfig.quality = Math.max(50, streamConfig.quality - 5);
          streamConfig.frameRate = Math.max(1, streamConfig.frameRate - 0.5);
          console.log(`High latency detected (${streamConfig.avgLatency.toFixed(0)}ms). Reducing quality to ${streamConfig.quality}%`);
          
          if (recognitionInterval) {
            clearInterval(recognitionInterval);
            recognitionInterval = setInterval(getServerFrame, 1000 / streamConfig.frameRate);
          }
        } else if (streamConfig.avgLatency < 500) {  
          streamConfig.quality = Math.min(85, streamConfig.quality + 5);
          streamConfig.frameRate = Math.min(4, streamConfig.frameRate + 0.5);
          console.log(`Low latency (${streamConfig.avgLatency.toFixed(0)}ms). Increasing quality to ${streamConfig.quality}%`);
          
          if (recognitionInterval) {
            clearInterval(recognitionInterval);
            recognitionInterval = setInterval(getServerFrame, 1000 / streamConfig.frameRate);
          }
        }
      }

      if (data.image) {
        const cameraFeed = document.getElementById("cameraFeed");
        if (cameraFeed) {
          cameraFeed.src = "data:image/jpeg;base64," + data.image;
        }
      }
      
      displayResult({
        recognized: data.recognized || false,
        name: data.name || null,
        confidence: data.confidence || 0,
        quality_score: data.quality_score || 0,
        processing_time: data.processing_time || 0,
        method_used: data.method_used || 'http',
        message: data.message || (data.recognized ? `Recognized ${data.name}` : 'Unknown person'),
        error: data.error || false,
        confidence_level: data.confidence_level || 'unknown',
        environment: data.environment,
        all_faces: data.all_faces
      });
      
      updateCurrentResult({
        recognized: data.recognized || false,
        name: data.name || null,
        confidence: data.confidence || 0,
        quality_score: data.quality_score || 0,
        message: data.message || '',
        environment: data.environment,
        all_faces: data.all_faces,
        method_used: data.method_used || 'http',
        confidence_level: data.confidence_level || 'unknown'
      });
    })
    .catch((err) => {
      console.error("Frame error:", err);
      displayResult({
        recognized: false,
        name: null,
        confidence: 0,
        message: `Connection error: ${err.message}`,
        quality_score: 0,
        processing_time: 0,
        error: true,
      });
    });
}
function toggleStreamMode() {
  if (!recognitionActive) {
    showToast("Start recognition first", "warning", "Stream Mode");
    return;
  }
  
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
    recognitionInterval = null;
  }
  
  useWebSocket = !useWebSocket;
  
  if (useWebSocket) {
    initWebSocketStream();
  } else {
    initHTTPStream();
  }
  
  const modeBtn = document.getElementById('toggleStreamModeBtn');
  if (modeBtn) {
    modeBtn.textContent = useWebSocket ? 'Use HTTP' : 'Use WebSocket';
  }
}


function toggleBoundingBoxes() {
  streamConfig.drawBoxes = !streamConfig.drawBoxes;
  const button = document.getElementById('toggleBoxesBtn');
  if (button) {
    button.textContent = streamConfig.drawBoxes ? 'Hide Boxes' : 'Show Boxes';
    button.className = streamConfig.drawBoxes ? 'button start' : 'button stop';
  }
  showToast(
    `Bounding boxes ${streamConfig.drawBoxes ? 'enabled' : 'disabled'}`,
    'info',
    'Display Settings'
  );
}

function increaseQuality() {
  streamConfig.quality = Math.min(95, streamConfig.quality + 10);
  showToast(`Quality increased to ${streamConfig.quality}%`, 'info', 'Quality Control');
}

function decreaseQuality() {
  streamConfig.quality = Math.max(40, streamConfig.quality - 10);
  showToast(`Quality decreased to ${streamConfig.quality}%`, 'info', 'Quality Control');
}

function increaseFrameRate() {
  streamConfig.frameRate = Math.min(5, streamConfig.frameRate + 0.5);
  if (recognitionInterval && recognitionActive) {
    clearInterval(recognitionInterval);
    recognitionInterval = setInterval(getServerFrame, 1000 / streamConfig.frameRate);
  }
  showToast(`Frame rate increased to ${streamConfig.frameRate.toFixed(1)} FPS`, 'info', 'Frame Rate');
}

function decreaseFrameRate() {
  streamConfig.frameRate = Math.max(0.5, streamConfig.frameRate - 0.5);
  if (recognitionInterval && recognitionActive) {
    clearInterval(recognitionInterval);
    recognitionInterval = setInterval(getServerFrame, 1000 / streamConfig.frameRate);
  }
  showToast(`Frame rate decreased to ${streamConfig.frameRate.toFixed(1)} FPS`, 'info', 'Frame Rate');
}

function updateStreamInfo() {
  const infoElement = document.getElementById('streamInfo');
  if (infoElement && recognitionActive) {
    infoElement.innerHTML = `
      <div style="font-size: 0.85em; color: var(--text-secondary); margin-top: 10px;">
        Stream: ${streamConfig.frameRate.toFixed(1)} FPS | 
        Quality: ${streamConfig.quality}% | 
        Latency: ${streamConfig.avgLatency.toFixed(0)}ms
      </div>
    `;
  }
}

setInterval(updateStreamInfo, 2000);

function updateCurrentResult(data) {
  const currentResult = document.getElementById("currentResult");

  let confidence = data.confidence;
  if (confidence > 1.0) {
    confidence = confidence / 100.0;
  }

  const hasEnvironment = data.environment && data.environment.scene;
  const hasMultipleFaces = data.all_faces && data.all_faces.length > 1;

  if (!data.recognized && !data.error) {
    let html = `
      <div style="padding: 18px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px; margin-top: 18px; border-left: 4px solid #6c757d;">
        <div style="font-weight: 600; color: #495057; font-size: 1.1em;">Unknown Person</div>
        <div style="font-size: 0.95em; margin-top: 8px; color: #6c757d;">
          Quality: ${(data.quality_score * 100).toFixed(1)}%
          ${data.method_used ? ` • Method: ${formatMethod(data.method_used)}` : ""}
        </div>
        <div class="confidence-bar">
          <div class="confidence-fill" style="width: ${confidence * 100}%; background: #ff9800;"></div>
        </div>`;

    if (hasEnvironment) {
      html += `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
          <div style="font-weight: 600; color: #6c757d; margin-bottom: 8px;">
            Environment: ${formatSceneName(data.environment.scene.scene)}
            <span style="font-size: 0.85em; color: #00bcd4;">
              (${(data.environment.scene.confidence * 100).toFixed(0)}% confidence)
            </span>
          </div>
          ${data.environment.environment_description ?
          `<div style="font-size: 0.9em; color: #6c757d; font-style: italic;">
              ${data.environment.environment_description}
            </div>` : ''}
        </div>`;
    }

    html += `</div>`;
    currentResult.innerHTML = html;

  } else if (data.recognized) {
    let html = `
      <div style="padding: 18px; background: linear-gradient(135deg, #e8f5e8, #f1f8e9); border-radius: 12px; margin-top: 18px; border-left: 4px solid #4caf50;">
        <div style="font-weight: 700; color: #2e7d32; font-size: 1.2em;">
          ${data.name}
          <span class="confidence-level conf-${data.confidence_level || "medium"}">
            ${formatConfidenceLevel(data.confidence_level || "medium")}
          </span>
        </div>
        <div style="font-size: 0.95em; margin-top: 10px; color: #4caf50; font-weight: 500;">
          Confidence: ${(confidence * 100).toFixed(1)}% • 
          Quality: ${(data.quality_score * 100).toFixed(1)}%
          ${data.method_used ? ` • ${formatMethod(data.method_used)}` : ""}
        </div>
        <div class="confidence-bar">
          <div class="confidence-fill" style="width: ${confidence * 100}%;"></div>
        </div>`;

    if (hasEnvironment) {
      const sceneConfColor = data.environment.scene.confidence > 0.7 ? '#4caf50' : data.environment.scene.confidence > 0.5 ? '#ff9800' : '#f44336';

      html += `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #c8e6c9;">
          <div style="font-weight: 600; color: #2e7d32; margin-bottom: 8px;">
            Location: ${formatSceneName(data.environment.scene.scene)}
            <span style="font-size: 0.85em; color: ${sceneConfColor};">
              (${(data.environment.scene.confidence * 100).toFixed(0)}% confidence)
            </span>
          </div>
          ${data.environment.environment_description ?
          `<div style="font-size: 0.9em; color: #4caf50; font-style: italic;">
              ${data.environment.environment_description}
            </div>` : ''}
          
          ${data.environment.object_summary && data.environment.object_summary.total_objects > 0 ?
          `<div style="margin-top: 8px; font-size: 0.85em; color: #6c757d;">
              ${data.environment.object_summary.total_objects} objects detected
              ${data.environment.object_summary.primary_objects ?
            ': ' + data.environment.object_summary.primary_objects.slice(0, 3).join(', ') : ''}
            </div>` : ''}
        </div>`;
    }

    if (hasMultipleFaces) {
      const recognizedPeople = data.all_faces.filter(f => f.recognized).map(f => f.name);
      const unknownCount = data.all_faces.filter(f => !f.recognized).length;

      html += `
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #c8e6c9;">
          <div style="font-weight: 600; color: #2e7d32; margin-bottom: 8px;">
            Multiple People Detected (${data.all_faces.length} total)
          </div>
          ${recognizedPeople.length > 0 ?
          `<div style="font-size: 0.9em; color: #4caf50;">
              Recognized: ${recognizedPeople.join(', ')}
            </div>` : ''}
          ${unknownCount > 0 ?
          `<div style="font-size: 0.9em; color: #ff9800;">
              ${unknownCount} unknown person(s)
            </div>` : ''}
        </div>`;
    }

    html += `</div>`;
    currentResult.innerHTML = html;

  } else if (data.error) {
    currentResult.innerHTML = `
      <div style="padding: 18px; background: linear-gradient(135deg, #ffebee, #fce4ec); border-radius: 12px; margin-top: 18px; border-left: 4px solid #f44336;">
        <div style="font-weight: 600; color: #c62828; font-size: 1.1em;">Error: ${data.message}</div>
      </div>`;
  }
}

function formatSceneName(scene) {
  if (!scene) return 'Unknown';
  return scene.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}


function displayResult(data) {
  let resultsDiv = document.getElementById("results");
  let resultClass = data.error
    ? "error"
    : data.recognized
      ? "recognized"
      : "unknown";

  let confidence = data.confidence || 0;
  if (confidence > 1.0) {
    confidence = confidence / 100.0;
  }

  let quality = data.quality_score || 0;
  let processingTime = data.processing_time || 0;

  let message = data.error
    ? `${data.message}`
    : data.recognized
      ? `${data.name}`
      : `Unknown person`;

  let confidenceLevel = data.confidence_level || "unknown";
  let methodUsed = data.method_used || "standard";

  let resultHtml = `
<div class="recognition-result ${resultClass}">
    <div class="result-header">
        ${new Date().toLocaleTimeString()} - ${message}
        ${data.recognized
      ? `<span class="confidence-level conf-${confidenceLevel}">${formatConfidenceLevel(
        confidenceLevel
      )}</span>`
      : ""
    }
    </div>
    <div class="result-details">
        Confidence: ${(confidence * 100).toFixed(1)}% • 
        Quality: ${(quality * 100).toFixed(1)}% • 
        Processing: ${(processingTime * 1000).toFixed(0)}ms • 
        Method: ${formatMethod(methodUsed)}
    </div>
    <div class="confidence-bar">
        <div class="confidence-fill" style="width: ${confidence * 100}%; ${!data.recognized ? "background: #ff9800;" : ""
    }"></div>
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
  fetch("/api/analytics_enhanced")
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
        "recognitionRate",
        "avgTime",
        "totalRequests",
        "enhancedMethods",
      ];
      analyticsElements.forEach((elementId) => {
        const element = document.getElementById(elementId);
        if (element) element.textContent = "0";
      });
    });
}

function updateAnalyticsDisplay(data) {
  if (data && data.recognition_stats) {
    let stats = data.recognition_stats;
    let rate =
      stats.total_requests > 0
        ? (
          (stats.successful_recognitions / stats.total_requests) *
          100
        ).toFixed(1)
        : 0;

    const recognitionRateEl = document.getElementById("recognitionRate");
    const avgTimeEl = document.getElementById("avgTime");
    const totalRequestsEl = document.getElementById("totalRequests");
    const enhancedMethodsEl = document.getElementById("enhancedMethods");

    if (recognitionRateEl) recognitionRateEl.textContent = rate + "%";
    if (avgTimeEl)
      avgTimeEl.textContent =
        (stats.avg_processing_time * 1000).toFixed(0) + "ms";
    if (totalRequestsEl) totalRequestsEl.textContent = stats.total_requests;

    let enhancedCount =
      (stats.weighted_average_applied || 0) +
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
  const chartDiv = document.getElementById("methodChart");
  const total = Object.values(methodData).reduce((a, b) => a + b, 0);

  if (total === 0) {
    chartDiv.innerHTML = `
      <div class="empty-state">
        <h3>No Method Data Available</h3>
        <p>Method usage statistics will appear here once recognition activities begin.</p>
      </div>`;
    return;
  }

  let html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">';

  Object.entries(methodData).forEach(([method, count]) => {
    const percentage = ((count / total) * 100).toFixed(1);
    const displayMethod = formatMethod(method);
    const methodClass = method.includes("enhanced")
      ? "enhanced"
      : method.includes("standard")
        ? "standard"
        : method.split("_")[0];

    html += `
      <div class="method-badge method-${methodClass}" 
           style="flex: 1; min-width: 140px; text-align: center; padding: 15px;">
        ${displayMethod}<br>
        <strong>${count} (${percentage}%)</strong>
      </div>`;
  });

  html += "</div>";
  chartDiv.innerHTML = html;
}

function updateConfidenceChart(recognitions) {
  const chartDiv = document.getElementById("confidenceChart");

  if (!recognitions || recognitions.length === 0) {
    chartDiv.innerHTML = `
      <div class="empty-state">
        <h3>No Confidence Data Available</h3>
        <p>Confidence level distribution will be displayed here after recognition activities.</p>
      </div>`;
    return;
  }

  const levels = { very_high: 0, high: 0, medium: 0, low: 0, very_low: 0 };

  recognitions.forEach((rec) => {
    if (rec.confidence_level && levels.hasOwnProperty(rec.confidence_level)) {
      levels[rec.confidence_level] += rec.recognition_count || 1;
    }
  });

  const total = Object.values(levels).reduce((a, b) => a + b, 0);

  if (total === 0) {
    chartDiv.innerHTML = `
      <div class="empty-state">
        <h3>No Confidence Data</h3>
        <p>No valid confidence levels found in recognition data.</p>
      </div>`;
    return;
  }

  let html = '<div style="display: flex; flex-wrap: wrap; gap: 15px;">';

  Object.entries(levels).forEach(([level, count]) => {
    const percentage = ((count / total) * 100).toFixed(1);
    html += `
      <div class="confidence-level conf-${level}" 
           style="flex: 1; min-width: 120px; text-align: center; padding: 18px;">
        <strong>${count}</strong><br>
        ${formatConfidenceLevel(level)}<br>
        <small>(${percentage}%)</small>
      </div>`;
  });

  html += "</div>";
  chartDiv.innerHTML = html;
}

function updateConfidenceChart(recognitions) {
  const chartDiv = document.getElementById("confidenceChart");

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

  recognitions.forEach((rec) => {
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

  html += "</div>";
  chartDiv.innerHTML = html;
}

function updateHourlyChart(hourlyData) {
  const chartDiv = document.getElementById("hourlyChart");

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
                    ${count > 0
        ? `title='${count} recognitions at ${hour}:00'`
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
      loadRecognitionLogs(date);
      loadHistoricalData(date);
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

function loadRecognitionLogs(date) {
  const logsDiv = document.getElementById("recognitionLogs");
  if (logsDiv) {
    logsDiv.innerHTML =
      '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading recognition logs...</div>';
  }

  fetch(`/api/recognition_logs?date=${date}`)
    .then((response) => response.json())
    .then((data) => {
      displayRecognitionLogs(data);
    })
    .catch((err) => {
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
  const historicalDiv = document.getElementById("historicalData");
  if (historicalDiv) {
    historicalDiv.innerHTML =
      '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading historical data...</div>';
  }

  fetch(`/api/historical_data?date=${date}`)
    .then((response) => response.json())
    .then((data) => {
      displayHistoricalData(data);
    })
    .catch((err) => {
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
  showToast("Generating test data...", "info", "Processing");

  fetch("/api/generate_test_data", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        showToast(
          "Test data generated successfully! Refreshing reports...",
          "success",
          "Data Generated"
        );
        setTimeout(() => loadDailyReport(), 1000);
      } else {
        showToast(
          `Failed to generate test data: ${data.error}`,
          "error",
          "Generation Failed"
        );
      }
    })
    .catch((err) => {
      showToast(
        `Error generating test data: ${err.message}`,
        "error",
        "Generation Error"
      );
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
    </div>`;
    return;
  }

  if (!report.summary || (report.summary.total_recognitions || 0) === 0) {
    reportContent.innerHTML = `
    <div class="empty-state">
        <h3>No Activity Recorded</h3>
        <p><strong>Date:</strong> ${report.date || document.getElementById("reportDate")?.value}</p>
        <p>No face recognitions were performed on this date.</p>
        <p>Try using the "Generate Test Data" button to create sample data for testing.</p>
    </div>`;
    return;
  }

  let avgConfidence = report.summary.avg_confidence || 0;
  if (avgConfidence > 1) {
    avgConfidence = avgConfidence / 100;
  }

  let avgQuality = report.summary.avg_quality || 0;

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
        <div class="stat-value">${(avgConfidence * 100).toFixed(1)}%</div>
        <div class="stat-label">Recognition accuracy</div>
    </div>
    <div class="stat-card method-card">
        <h4>Avg Quality</h4>
        <div class="stat-value">${(avgQuality * 100).toFixed(1)}%</div>
        <div class="stat-label">Image quality</div>
    </div>
</div>`;

  if (report.performance_insights && report.performance_insights.length > 0) {
    html += `
    <div class="chart-container">
        <h3 class="section-title">Performance Insights</h3>
        <ul class="insights-list">
            ${report.performance_insights.map((insight) => `<li>${insight}</li>`).join("")}
        </ul>
    </div>`;
  }

  if (report.people_analysis && report.people_analysis.length > 0) {
    html += `
    <div class="chart-container">
        <h3 class="section-title">Most Active Subjects</h3>
        <div class="people-list">`;

    report.people_analysis.slice(0, 6).forEach((person) => {
      let personConfidence = person.avg_confidence || 0;
      if (personConfidence > 1) {
        personConfidence = personConfidence / 100;
      }

      html += `
        <div class="person-card">
            <div class="person-name">${person.name}</div>
            <div class="person-stats">
                <div><strong>Recognitions:</strong> ${person.recognition_count}</div>
                <div><strong>Avg Confidence:</strong> ${(personConfidence * 100).toFixed(1)}%</div>
                <div><strong>Avg Quality:</strong> ${(person.avg_quality * 100).toFixed(1)}%</div>
                <div><strong>Method:</strong> ${formatMethod(person.most_used_method)}</div>
            </div>
            <div style="margin-top: 15px;">
                <span class="confidence-level conf-${person.confidence_level}">
                    ${formatConfidenceLevel(person.confidence_level)}
                </span>
            </div>
        </div>`;
    });

    html += "</div></div>";
  }

  if (report.confidence_distribution) {
    html += `
    <div class="chart-container">
        <h3 class="section-title">Confidence Distribution</h3>
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">`;

    Object.entries(report.confidence_distribution).forEach(([level, count]) => {
      const total = Object.values(report.confidence_distribution).reduce((a, b) => a + b, 0);
      const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;

      html += `
        <div class="confidence-level conf-${level}" style="flex: 1; min-width: 120px; text-align: center; padding: 18px;">
            <strong>${count}</strong><br>
            ${formatConfidenceLevel(level)}<br>
            <small>(${percentage}%)</small>
        </div>`;
    });

    html += "</div></div>";
  }

  reportContent.innerHTML = html;
}

function displayRecognitionLogs(data) {
  const logsDiv = document.getElementById("recognitionLogs");
  if (!logsDiv) return;

  if (!data.logs || data.logs.length === 0) {
    logsDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Recognition Logs</h3>
        <p>No face recognition logs found for this date.</p>
        <p>Try using the "Generate Test Data" button to create sample data.</p>
    </div>`;
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
        <tbody>`;

  data.logs.forEach((log, index) => {
    const time = new Date(log.timestamp).toLocaleTimeString();

    let logConfidence = log.confidence || 0;
    if (logConfidence > 1) {
      logConfidence = logConfidence / 100;
    }

    const confidenceColor = logConfidence > 0.8 ? "#4caf50" : logConfidence > 0.6 ? "#8bc34a" : logConfidence > 0.4 ? "#ffc107" : "#f44336";
    const rowBg = index % 2 === 0 ? "background: white;" : "background: #f8f9fa;";

    html += `
    <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;" 
        onmouseover="this.style.background='#e3f2fd'" 
        onmouseout="this.style.background='${index % 2 === 0 ? "white" : "#f8f9fa"}'">
        <td style="padding: 12px 15px; font-weight: 500;">${time}</td>
        <td style="padding: 12px 15px; font-weight: 700; color: #333;">${log.person_name || "Unknown"}</td>
        <td style="padding: 12px 15px;">
            <span style="color: ${confidenceColor}; font-weight: 700;">${(logConfidence * 100).toFixed(1)}%</span>
        </td>
        <td style="padding: 12px 15px; font-weight: 600;">${(log.quality_score * 100).toFixed(1)}%</td>
        <td style="padding: 12px 15px;">
            <span class="method-badge method-${log.method_used.split("_")[0]}">${formatMethod(log.method_used)}</span>
        </td>
        <td style="padding: 12px 15px; font-weight: 500;">${(log.processing_time * 1000).toFixed(0)}ms</td>
    </tr>`;
  });

  let avgConfidence = data.avg_confidence || 0;
  if (avgConfidence > 1) {
    avgConfidence = avgConfidence / 100;
  }

  let avgQuality = data.avg_quality || 0;

  html += `
        </tbody>
    </table>
</div>
<div style="margin-top: 20px; padding: 15px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 10px; font-size: 1em; color: #495057;">
    <strong>Summary:</strong> ${data.logs.length} total logs • 
    Avg confidence: <span style="font-weight: 700; color: #4caf50;">${(avgConfidence * 100).toFixed(1)}%</span> • 
    Avg quality: <span style="font-weight: 700; color: #2196f3;">${(avgQuality * 100).toFixed(1)}%</span>
</div>`;

  logsDiv.innerHTML = html;
}

function displayHistoricalData(data) {
  const historicalDiv = document.getElementById("historicalData");
  if (!historicalDiv) return;

  if (!data.days || data.days.length === 0) {
    historicalDiv.innerHTML = `
    <div class="empty-state">
        <h3>No Historical Data</h3>
        <p>Historical performance data will appear here once you have multiple days of recognition activity.</p>
        <p>Continue using the system to build up historical trends and insights.</p>
    </div>`;
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
            <tbody>`;

  data.days.forEach((day, index) => {
    const date = new Date(day.date).toLocaleDateString();
    const rowBg = index % 2 === 0 ? "background: white;" : "background: #f8f9fa;";

    let dayConfidence = day.avg_confidence || 0;
    if (dayConfidence > 1) {
      dayConfidence = dayConfidence / 100;
    }

    const confidenceColor = dayConfidence > 0.8 ? "#4caf50" : dayConfidence > 0.6 ? "#8bc34a" : dayConfidence > 0.4 ? "#ffc107" : "#f44336";

    html += `
    <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;"
        onmouseover="this.style.background='#e3f2fd'" 
        onmouseout="this.style.background='${index % 2 === 0 ? "white" : "#f8f9fa"}'">
        <td style="padding: 12px 15px; font-weight: 600;">${date}</td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 700; color: #333;">${day.total_recognitions}</td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${day.unique_people}</td>
        <td style="padding: 12px 15px; text-align: center;">
            <span style="color: ${confidenceColor}; font-weight: 700;">${(dayConfidence * 100).toFixed(1)}%</span>
        </td>
        <td style="padding: 12px 15px; text-align: center; font-weight: 600;">${(day.avg_quality * 100).toFixed(1)}%</td>
    </tr>`;
  });

  html += `
            </tbody>
        </table>
    </div>
</div>`;

  historicalDiv.innerHTML = html;
}

function loadPeopleList() {
  const peopleList = document.getElementById("peopleList");
  if (peopleList) {
    peopleList.innerHTML =
      '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading registered people...</div>';
  }

  fetch("/api/people")
    .then((response) => response.json())
    .then((data) => {
      displayPeopleList(data.people);
    })
    .catch((err) => {
      if (peopleList) {
        peopleList.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Database</h3>
                <p>Failed to load registered people: ${err.message}</p>
            </div>
        `;
      }
      showToast(
        `Failed to load people list: ${err.message}`,
        "error",
        "Load Error"
      );
    });
}

function displayPeopleList(people) {
  const peopleList = document.getElementById("peopleList");
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
        <div class="stat-value">${people.reduce(
    (sum, p) => sum + p.photo_count,
    0
  )}</div>
        <div class="stat-label">Training Images</div>
    </div>
    <div class="stat-card quality-card">
        <h4>Avg Quality</h4>
        <div class="stat-value">${(
      (people.reduce((sum, p) => sum + p.avg_quality, 0) / people.length) *
      100
    ).toFixed(1)}%</div>
        <div class="stat-label">Overall Quality</div>
    </div>
                 <div class="stat-card method-card">
         <h4>Multi-image</h4>
         <div class="stat-value">${people.filter((p) => p.registration_method === "enhanced").length
    }</div>
         <div class="stat-label">Multi-image Registration</div>
     </div>
</div>

<div class="people-list">
`;

  people.forEach((person) => {
    const registrationDate = new Date(person.created_at).toLocaleDateString();
    const qualityColor =
      person.avg_quality > 0.7
        ? "#4caf50"
        : person.avg_quality > 0.5
          ? "#ff9800"
          : "#f44336";

    html += `
    <div class="person-card">
        <div class="person-name">${person.name}</div>
        <div class="person-stats">
            <div><strong>Photos:</strong> <span style="color: #2196f3; font-weight: 700;">${person.photo_count
      }</span></div>
            <div><strong>Registered:</strong> ${registrationDate}</div>
            <div><strong>Avg Quality:</strong> 
                <span style="color: ${qualityColor}; font-weight: 700;">
                    ${(person.avg_quality * 100).toFixed(1)}%
                </span>
            </div>
            <div><strong>Best Quality:</strong> <span style="color: #4caf50; font-weight: 700;">${(
        person.best_quality * 100
      ).toFixed(1)}%</span></div>
        </div>
        <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center;">
          <span class="method-badge method-${person.registration_method}">
              ${person.registration_method === "enhanced"
        ? "Multi-image Registration"
        : "Standard Registration"
      }
          </span>
          <div style="display: flex; gap: 10px;">
              <button class="button add-person" style="padding: 10px 18px; font-size: 0.85em; margin: 0;" 
                      onclick="analyzePerson('${person.name}')">
                  Analyze
              </button>
              <button class="button stop" style="padding: 10px 18px; font-size: 0.85em; margin: 0;" 
                      onclick="deletePerson('${person.name}')">
                  Delete
              </button>
          </div>
      </div>
    </div>
`;
  });

  html += "</div>";
  peopleList.innerHTML = html;
}

function deletePerson(name) {
  const confirmed = confirm(
    `Are you sure you want to delete ${name} and all their face data?\n\nThis action cannot be undone.`
  );

  if (confirmed) {
    showToast(`Deleting ${name}...`, "info", "Processing");

    fetch("/api/delete_person", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: name }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showToast(
            `${name} has been successfully deleted.`,
            "success",
            "Person Deleted"
          );
          setTimeout(() => loadPeopleList(), 1000);
        } else {
          showToast(
            `Failed to delete ${name}: ${data.error}`,
            "error",
            "Deletion Failed"
          );
        }
      })
      .catch((err) => {
        showToast(
          `Error deleting ${name}: ${err.message}`,
          "error",
          "Deletion Error"
        );
      });
  }
}

function formatMethod(method) {
  const methodMap = {
    'standard': 'Standard',
    'weighted': 'Weighted Avg',
    'temporal': 'Temporal',
    'enhanced': 'Enhanced',
    'enhanced_matching': 'Enhanced Matching',
    'outlier_removed': 'Outlier Filtered',
    'weighted_average': 'Weighted Average',
    'adaptive': 'Adaptive',
    'low_confidence': 'Low Confidence',
    'no_face_detected': 'No Face',
    'error': 'Error'
  };

  if (!method || method === 'unknown') {
    return 'Standard';
  }
  
  if (method.includes('_')) {
    const parts = method.split('_');
    if (methodMap[method]) {
      return methodMap[method];
    }
    return parts.map(part => methodMap[part] || part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  }

  return methodMap[method] || method.charAt(0).toUpperCase() + method.slice(1);
}

function formatConfidenceLevel(level) {
  const levelMap = {
    very_high: "Very High",
    high: "High",
    medium: "Medium",
    low: "Low",
    very_low: "Very Low",
  };
  return levelMap[level] || level;
}

function initializeDashboard() {
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
        if (data.model_loaded) {
          statusEl.innerHTML = "System Ready - Model Loaded";
          statusEl.className = "status success";
          showToast("Face recognition started", "success", "System Ready");
        } else {
          statusEl.innerHTML = "Model Not Loaded - Check Server Logs";
          statusEl.className = "status warning";
          showToast(
            "System started but model not fully loaded",
            "warning",
            "Partial Initialization"
          );
        }
      }

      console.log("Server features:", data.features || {});
      console.log("Enhanced methods:", data.averaging_methods || {});
    })
    .catch((err) => {
      console.error("Initial health check failed:", err);
      const statusEl = document.getElementById("status");
      if (statusEl) {
        statusEl.innerHTML = "Cannot Connect to Server";
        statusEl.className = "status error";
      }
      showToast(
        "Cannot connect to face recognition server",
        "error",
        "Connection Failed"
      );
    });

  setDefaultReportDate();
}

function analyzePerson(name) {
  showToast(`Analyzing ${name}'s registration...`, "info", "Processing");

  fetch(`/api/analyze_person/${encodeURIComponent(name)}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        showToast(`Analysis failed: ${data.error}`, "error");
        return;
      }
      showAnalysisModal(data);
    })
    .catch((err) => {
      showToast(`Error analyzing person: ${err.message}`, "error");
    });
}

function showAnalysisModal(data) {
  const modalHtml = `
      <div class="modal analysis-modal show" id="analysisModal">
          <div class="modal-content">
              <div class="modal-header">
                  <h3 class="modal-title">Quality Analysis - ${data.name}</h3>
                  <button class="modal-close" onclick="closeAnalysisModal()">&times;</button>
              </div>
              <div class="modal-body">
                  <div class="analytics-grid" style="margin-bottom: 25px;">
                      <div class="stat-card recognition-card">
                          <h4>Photos</h4>
                          <div class="stat-value">${data.photo_count}</div>
                          <div class="stat-label">Total Images</div>
                      </div>
                      <div class="stat-card quality-card">
                          <h4>Average Quality</h4>
                          <div class="stat-value">${(
      data.avg_quality * 100
    ).toFixed(1)}%</div>
                          <div class="stat-label">Overall Score</div>
                      </div>
                      <div class="stat-card performance-card">
                          <h4>Best Quality</h4>
                          <div class="stat-value">${(
      data.max_quality * 100
    ).toFixed(1)}%</div>
                          <div class="stat-label">Highest Score</div>
                      </div>
                      <div class="stat-card method-card">
                          <h4>Worst Quality</h4>
                          <div class="stat-value">${(
      data.min_quality * 100
    ).toFixed(1)}%</div>
                          <div class="stat-label">Lowest Score</div>
                      </div>
                  </div>
                  
                  <div class="chart-container">
                      <h3 class="section-title">Photo Quality Distribution</h3>
                      <div class="photo-grid">
                          ${data.qualities
      .map(
        (quality, index) => `
                              <div class="photo-quality-item">
                                  <div class="quality-indicator ${getQualityClass(
          quality
        )}">
                                      Photo ${index + 1}
                                  </div>
                                  <div style="margin-top: 8px; font-weight: 600;">
                                      ${(quality * 100).toFixed(1)}%
                                  </div>
                              </div>
                          `
      )
      .join("")}
                      </div>
                  </div>
                  
                  ${generateRecommendations(data.recommendations)}
                  
                  <div style="text-align: center; margin-top: 30px;">
                      <button class="button secondary" onclick="closeAnalysisModal()">Close</button>
                  </div>
              </div>
          </div>
      </div>
  `;

  document.body.insertAdjacentHTML("beforeend", modalHtml);
}

function closeAnalysisModal() {
  const modal = document.getElementById("analysisModal");
  if (modal) {
    modal.remove();
  }
}

function getQualityClass(quality) {
  if (quality > 0.6) return "quality-excellent";
  if (quality > 0.3) return "quality-good";
  return "quality-poor";
}

function generateRecommendations(recommendations) {
  let html =
    '<div class="chart-container"><h3 class="section-title">Recommendations</h3>';

  if (recommendations.should_retake_photos) {
    html += `
          <div class="recommendation-card">
              <strong>Consider Re-registration</strong><br>
              Overall photo quality is low. Consider capturing new photos with better lighting and positioning.
          </div>
      `;
  }

  if (recommendations.needs_better_lighting) {
    html += `
          <div class="recommendation-card">
              <strong>Improve Lighting</strong><br>
              Many photos have poor lighting. Use natural light or well-lit environments for better results.
          </div>
      `;
  }

  if (recommendations.has_good_photos) {
    html += `
          <div class="recommendation-card" style="border-left-color: #4caf50;">
              <strong>Good Quality Detected</strong><br>
              Some photos have excellent quality. The system should recognize this person reliably.
          </div>
      `;
  }

  if (
    !recommendations.should_retake_photos &&
    !recommendations.needs_better_lighting &&
    !recommendations.has_good_photos
  ) {
    html += `
          <div class="recommendation-card">
              <strong>Analysis Complete</strong><br>
              Photo quality is acceptable for basic recognition. Consider adding more photos for improved accuracy.
          </div>
      `;
  }

  html += "</div>";
  return html;
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
        if (data.recognition_stats) {
          let stats = data.recognition_stats;
          let rate =
            stats.total_requests > 0
              ? (
                (stats.successful_recognitions / stats.total_requests) *
                100
              ).toFixed(1)
              : 0;

          const liveTab = document.getElementById("live-tab");
          if (liveTab && liveTab.classList.contains("active")) {
            if (!recognitionActive) {
              const statusEl = document.getElementById("status");
              if (statusEl) {
                if (!data.model_loaded) {
                  statusEl.innerHTML =
                    "Model Not Loaded - Basic Detection Only";
                  statusEl.className = "status warning";
                } else {
                  statusEl.innerHTML = "System Ready - Model Loaded";
                  statusEl.className = "status success";
                }
              }
            }
          }

          const analyticsTab = document.getElementById("analytics-tab");
          if (analyticsTab && analyticsTab.classList.contains("active")) {
            const elements = {
              recognitionRate: rate + "%",
              avgTime: (stats.avg_processing_time * 1000).toFixed(0) + "ms",
              totalRequests: stats.total_requests,
              enhancedMethods:
                (stats.weighted_average_applied || 0) +
                (stats.temporal_smoothing_applied || 0) +
                (stats.outliers_removed || 0),
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
  }, 5000);
}

document.addEventListener("DOMContentLoaded", function () {
  if (typeof io === 'undefined') {
    console.warn("Socket.IO not loaded - WebSocket will be disabled");
    useWebSocket = false;
  } else {
    console.log("Socket.IO library loaded");
  }
  initializeDashboard();
  startPeriodicUpdates();

  const addPersonModal = document.getElementById("addPersonModal");
  if (addPersonModal) {
    addPersonModal.addEventListener("click", function (e) {
      if (e.target === this) {
        closeAddPersonModal();
      }
    });
  }

  const form = document.getElementById("addPersonForm");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const personName = document.getElementById("personName").value.trim();

      if (!personName) {
        showToast("Please enter a person name", "error");
        return;
      }

      if (capturedImages.length === 0) {
        showToast("Please capture at least one image", "error");
        return;
      }

      const submitBtn = document.getElementById("submitBtn");
      submitBtn.disabled = true;
      submitBtn.textContent = "Adding Person...";

      const validImages = capturedImages.filter((img) => isValidBase64(img));
      if (validImages.length !== capturedImages.length) {
        showToast(
          `${capturedImages.length - validImages.length
          } invalid images detected`,
          "warning"
        );
      }

      if (validImages.length < 3) {
        showToast(
          "Not enough valid images. Please capture more images.",
          "error"
        );
        submitBtn.disabled = false;
        submitBtn.textContent = "Add Person";
        return;
      }

      const formData = {
        name: personName,
        images: validImages,
      };

      fetch("/api/register_enhanced", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      })
        .then((response) => {
          if (!response.ok) {
            return response.json().then((err) => Promise.reject(err));
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            showToast(
              `${personName} added successfully with ${data.photos_processed} valid images!`,
              "success"
            );

            if (data.quality_analysis) {
              const qa = data.quality_analysis;
              setTimeout(() => {
                showToast(
                  `Quality Analysis: ${qa.valid_images}/${qa.total_images
                  } images processed. Average quality: ${(
                    qa.average_quality * 100
                  ).toFixed(1)}%`,
                  "info",
                  "Registration Details",
                  6000
                );
              }, 2000);
            }

            closeAddPersonModal();
            const peopleTab = document.getElementById("people-tab");
            if (peopleTab && peopleTab.classList.contains("active")) {
              loadPeopleList();
            }
          } else {
            showToast(
              `Failed to add person: ${data.message || data.error}`,
              "error"
            );
          }
        })
        .catch((err) => {
          console.error("Add person error:", err);
          const errorMessage =
            err.error || err.message || "Unknown error occurred";
          showToast(`Error adding person: ${errorMessage}`, "error");
        })
        .finally(() => {
          submitBtn.disabled = false;
          submitBtn.textContent = "Add Person";
        });
    });
  }
});

function loadEnhancedAnalytics() {
  fetch('/api/environment/statistics?days=7')
    .then(response => response.json())
    .then(data => {
      displayEnvironmentStats(data);
    })
    .catch(err => {
      console.error('Environment stats error:', err);
    });

  fetch('/api/multi_person/statistics?days=7')
    .then(response => response.json())
    .then(data => {
      displayMultiPersonStats(data);
    })
    .catch(err => {
      console.error('Multi-person stats error:', err);
    });
}

function displayEnvironmentStats(data) {
  const container = document.getElementById('environmentStats');
  if (!container) return;

  if (!data.scenes || data.scenes.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>No Environment Data</h3>
        <p>Environment detection data will appear here once the system starts analyzing scenes.</p>
      </div>
    `;
    return;
  }

  let html = `
    <div class="analytics-grid" style="margin-bottom: 25px;">
      <div class="stat-card recognition-card">
        <h4>Total Detections</h4>
        <div class="stat-value">${data.total_detections}</div>
        <div class="stat-label">Environment Analyses</div>
      </div>
      <div class="stat-card performance-card">
        <h4>Unique Scenes</h4>
        <div class="stat-value">${data.scenes.length}</div>
        <div class="stat-label">Different Locations</div>
      </div>
      <div class="stat-card quality-card">
        <h4>Objects Detected</h4>
        <div class="stat-value">${Object.keys(data.most_common_objects).length}</div>
        <div class="stat-label">Unique Object Types</div>
      </div>
      <div class="stat-card method-card">
        <h4>Top Scene</h4>
        <div class="stat-value">${data.scenes[0] ? formatSceneName(data.scenes[0].scene) : 'N/A'}</div>
        <div class="stat-label">Most Common</div>
      </div>
    </div>

    <div class="chart-container">
      <h3 class="section-title">Scene Distribution</h3>
      <div class="scene-chart">
  `;

  const maxCount = Math.max(...data.scenes.map(s => s.occurrences));

  data.scenes.forEach(scene => {
    const percentage = (scene.occurrences / data.total_detections) * 100;
    const barWidth = (scene.occurrences / maxCount) * 100;
    const confidenceColor = scene.avg_confidence > 0.7 ? '#4caf50' :
      scene.avg_confidence > 0.5 ? '#ff9800' : '#f44336';

    html += `
      <div class="scene-item">
        <div class="scene-label">
          <strong>${formatSceneName(scene.scene)}</strong>
          <span style="color: ${confidenceColor}; font-size: 0.85em;">
            ${(scene.avg_confidence * 100).toFixed(0)}% confidence
          </span>
        </div>
        <div class="scene-bar-container">
          <div class="scene-bar" style="width: ${barWidth}%; background: linear-gradient(135deg, #4facfe, #00f2fe);"></div>
        </div>
        <div class="scene-count">${scene.occurrences} (${percentage.toFixed(1)}%)</div>
      </div>
    `;
  });

  html += `
      </div>
    </div>

    <div class="chart-container">
      <h3 class="section-title">Most Detected Objects</h3>
      <div class="objects-grid">
  `;

  Object.entries(data.most_common_objects)
    .slice(0, 12)
    .forEach(([object, count]) => {
      html += `
        <div class="object-badge">
          <div class="object-name">${formatObjectName(object)}</div>
          <div class="object-count">${count}</div>
        </div>
      `;
    });

  html += `
      </div>
    </div>
  `;

  container.innerHTML = html;
}

function displayMultiPersonStats(data) {
  const container = document.getElementById('multiPersonStats');
  if (!container) return;

  if (data.total_multi_person_sessions === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <h3>No Multi-Person Data</h3>
        <p>Multi-person detection data will appear here when multiple people are detected together.</p>
      </div>
    `;
    return;
  }

  let html = `
    <div class="analytics-grid" style="margin-bottom: 25px;">
      <div class="stat-card recognition-card">
        <h4>Multi-Person Sessions</h4>
        <div class="stat-value">${data.total_multi_person_sessions}</div>
        <div class="stat-label">Multiple People Detected</div>
      </div>
      <div class="stat-card performance-card">
        <h4>Common Groups</h4>
        <div class="stat-value">${data.common_combinations.length}</div>
        <div class="stat-label">Unique Combinations</div>
      </div>
    </div>

    <div class="chart-container">
      <h3 class="section-title">Common Person Combinations</h3>
      <div class="combinations-list">
  `;

  if (data.common_combinations.length === 0) {
    html += '<p class="text-muted">No recurring combinations detected yet.</p>';
  } else {
    data.common_combinations.forEach((combo, index) => {
      html += `
        <div class="combination-item">
          <div class="combination-rank">#${index + 1}</div>
          <div class="combination-people">${combo.people}</div>
          <div class="combination-count">${combo.occurrences} times</div>
        </div>
      `;
    });
  }

  html += `
      </div>
    </div>
  `;

  container.innerHTML = html;
}

function loadEnhancedLogs(date = null) {
  const logsDiv = document.getElementById('enhancedLogs');
  if (!logsDiv) return;

  logsDiv.innerHTML = '<div style="text-align: center; padding: 40px;"><span class="loading-spinner"></span>Loading enhanced logs...</div>';

  const url = date ? `/api/enhanced_logs?date=${date}&limit=100` : '/api/enhanced_logs?limit=100';

  fetch(url)
    .then(response => response.json())
    .then(data => {
      displayEnhancedLogs(data.logs);
    })
    .catch(err => {
      logsDiv.innerHTML = `
        <div class="empty-state">
          <h3>Error Loading Logs</h3>
          <p>${err.message}</p>
        </div>
      `;
    });
}

function displayEnhancedLogs(logs) {
  const logsDiv = document.getElementById('enhancedLogs');
  if (!logsDiv) return;

  if (!logs || logs.length === 0) {
    logsDiv.innerHTML = `
      <div class="empty-state">
        <h3>No Enhanced Logs</h3>
        <p>Enhanced recognition logs will appear here once you start using the enhanced recognition system.</p>
      </div>
    `;
    return;
  }

  let html = `
    <div style="max-height: 600px; overflow-y: auto; border: 2px solid #e0e0e0; border-radius: 15px; padding: 20px; background: #fafafa;">
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); font-weight: 700;">
            <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Time</th>
            <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">People</th>
            <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Environment</th>
            <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Objects</th>
            <th style="padding: 15px; text-align: left; border-bottom: 3px solid #dee2e6;">Confidence</th>
          </tr>
        </thead>
        <tbody>
  `;

  logs.forEach((log, index) => {
    const time = new Date(log.timestamp).toLocaleTimeString();
    const rowBg = index % 2 === 0 ? 'background: white;' : 'background: #f8f9fa;';

    const peopleText = log.people_detected > 0
      ? (log.all_people && log.all_people.length > 0
        ? log.all_people.filter(p => p).join(', ')
        : `${log.people_detected} person(s)`)
      : 'No faces';

    const sceneText = log.scene_type !== 'unknown'
      ? formatSceneName(log.scene_type)
      : 'Unknown';

    const sceneConfColor = log.scene_confidence > 0.7 ? '#4caf50' :
      log.scene_confidence > 0.5 ? '#ff9800' : '#f44336';

    const envDesc = log.environment_description || 'No environment data';

    html += `
      <tr style="${rowBg} border-bottom: 1px solid #e9ecef; transition: all 0.3s ease;" 
          onmouseover="this.style.background='#e3f2fd'" 
          onmouseout="this.style.background='${index % 2 === 0 ? 'white' : '#f8f9fa'}'">
        <td style="padding: 12px 15px; font-weight: 500;">${time}</td>
        <td style="padding: 12px 15px; font-weight: 600; color: #333;">
          ${peopleText}
          ${log.people_detected > 1 ? '<span style="color: #2196f3; font-size: 0.85em;"> (Multi)</span>' : ''}
        </td>
        <td style="padding: 12px 15px;">
          <div style="font-weight: 600;">${sceneText}</div>
          <div style="font-size: 0.85em; color: ${sceneConfColor};">
            ${(log.scene_confidence * 100).toFixed(0)}% confidence
          </div>
        </td>
        <td style="padding: 12px 15px; font-size: 0.9em;">
          ${log.object_count || 0} objects
        </td>
        <td style="padding: 12px 15px;">
          <span style="color: #4caf50; font-weight: 700;">
            ${(log.confidence * 100).toFixed(1)}%
          </span>
        </td>
      </tr>
      <tr style="${rowBg}">
        <td colspan="5" style="padding: 8px 15px; font-size: 0.9em; color: #666; border-bottom: 1px solid #e9ecef;">
          <em>${envDesc}</em>
        </td>
      </tr>
    `;
  });

  html += `
        </tbody>
      </table>
    </div>
  `;

  logsDiv.innerHTML = html;
}

function formatSceneName(scene) {
  if (!scene) return 'Unknown';
  return scene.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

function formatObjectName(object) {
  if (!object) return 'Unknown';
  return object.split('_').map(word =>
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

function switchToEnhancedTab(event, tabName) {
  switchTab(event, tabName);

  if (tabName === 'enhanced-analytics') {
    loadEnhancedAnalytics();
  } else if (tabName === 'enhanced-logs') {
    loadEnhancedLogs();
  }
}

setInterval(() => {
  const enhancedAnalyticsTab = document.getElementById('enhanced-analytics-tab');
  if (enhancedAnalyticsTab && enhancedAnalyticsTab.classList.contains('active')) {
    loadEnhancedAnalytics();
  }
}, 30000);

window.loadEnhancedAnalytics = loadEnhancedAnalytics;
window.loadEnhancedLogs = loadEnhancedLogs;
window.switchToEnhancedTab = switchToEnhancedTab;
window.toggleBoundingBoxes = toggleBoundingBoxes;
window.increaseQuality = increaseQuality;
window.decreaseQuality = decreaseQuality;
window.increaseFrameRate = increaseFrameRate;
window.decreaseFrameRate = decreaseFrameRate;
window.toggleStreamMode = toggleStreamMode;