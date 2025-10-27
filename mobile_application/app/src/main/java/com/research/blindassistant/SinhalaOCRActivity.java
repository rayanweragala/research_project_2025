package com.research.blindassistant;
import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Base64;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SinhalaOCRActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener, RecognitionListener {

    private static final String TAG = "SinhalaOCRActivity";
    private static final int AUDIO_PERMISSION_REQUEST = 101;
    private static final String SERVER_URL = "http://10.91.73.126:5002"; // OCR server port

    private TextView statusText, resultsText, instructionsText, performanceText, ocrConfidenceText;
    private Button btnStartOCR, btnStopOCR, btnBack, btnSpeak, btnCapture; // Added btnCapture
    private ImageView statusIndicator, documentFeedView;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private RequestQueue requestQueue;
    private ExecutorService executorService;
    private Handler mainHandler;

    private boolean isProcessing = false;
    private boolean isListening = false;
    private boolean serverConnected = false;
    private boolean serverCameraActive = false;
    private boolean isTtsReady = false;
    private boolean isReadingText = false;
    private boolean isCapturing = false; // Added isCapturing

    private int totalFramesReceived = 0;
    private int documentsProcessed = 0;
    private int successfulOCR = 0;

    private String lastExtractedText = "";
    private String lastDocumentType = "";
    private double lastOCRConfidence = 0.0;
    private double lastClassificationConfidence = 0.0;

    private long lastProcessingTime = 0;
    private long lastFrameRequestTime = 0;

    private final int PROCESSING_INTERVAL = 3000; // Process every 3 seconds
    private final int FRAME_REQUEST_INTERVAL = 500;

    private StatusManager statusManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_sinhala_ocr);

        statusManager = new StatusManager(this);
        statusManager.updateStatus(StatusManager.ConnectionStatus.DISCONNECTED,
                "OCR Server Disconnected", "Connecting to server...");

        initializeComponents();
        checkPermissions();
        setupVoiceRecognition();
        setupButtons(); // Buttons set up after initialization
        addHapticFeedback();

        requestQueue = Volley.newRequestQueue(this);
        executorService = Executors.newFixedThreadPool(2);
        mainHandler = new Handler(Looper.getMainLooper());

        testServerConnection();

        // Welcome message in both languages - Updated to mention capture
        speak("සිංහල ඕ සී ආර් පද්ධතිය සූදානම්");  // Sinhala OCR system ready
        mainHandler.postDelayed(() -> {
            speak("Sinhala OCR system ready. Say 'CAPTURE' or 'ග්‍රහණය' for single photo.");
        }, 2000);
    }

    private void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        resultsText = findViewById(R.id.resultsText);
        instructionsText = findViewById(R.id.instructionsText);
        performanceText = findViewById(R.id.performanceText);
        ocrConfidenceText = findViewById(R.id.ocrConfidenceText);

        btnStartOCR = findViewById(R.id.btnStartOCR);
        btnStopOCR = findViewById(R.id.btnStopOCR);
        btnBack = findViewById(R.id.btnBack);
        btnSpeak = findViewById(R.id.btnSpeak);
        btnCapture = findViewById(R.id.btnCapture); // Added initialization

        statusIndicator = findViewById(R.id.statusIndicator);
        documentFeedView = findViewById(R.id.documentFeedView);

        // Update instructions - Updated to mention capture
        updateInstructions("OCR system ready! Say 'START'/'ආරම්භ කරන්න' for continuous scan or 'CAPTURE'/'ග්‍රහණය' for single photo.");
        ttsEngine = new TextToSpeech(this, this);
    }

    private void checkPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO},
                    AUDIO_PERMISSION_REQUEST);
        }
    }

    private void setupVoiceRecognition() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(this);
        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        // Support both Sinhala and English
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "si-LK");
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "si-LK");
        ArrayList<String> languages = new ArrayList<>();
        languages.add("si-LK");  // Sinhala
        languages.add("en-US");  // English
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_SUPPORTED_LANGUAGES, languages);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
    }

    private void setupButtons() {
        btnStartOCR.setOnClickListener(v -> startOCRProcessing());
        btnStopOCR.setOnClickListener(v -> stopOCRProcessing());
        btnSpeak.setOnClickListener(v -> speakExtractedText());
        btnCapture.setOnClickListener(v -> captureAndProcessDocument()); // Added listener
        btnBack.setOnClickListener(v -> {
            speak("ආපසු යනවා");  // Going back in Sinhala
            mainHandler.postDelayed(() -> speak("Returning to main menu"), 1500);
            mainHandler.postDelayed(this::finish, 3000);
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnStartOCR, btnStopOCR, btnBack, btnSpeak, btnCapture}; // Added btnCapture
        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("බොත්තම: " + buttonText);  // Button: in Sinhala
                mainHandler.postDelayed(() -> speak("Button: " + buttonText), 1500);
                return true;
            });
        }
    }

    private void testServerConnection() {
        String url = SERVER_URL + "/api/health";
        @SuppressLint("DefaultLocale") JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        String status = response.getString("status");
                        if ("healthy".equals(status)) {
                            serverConnected = true;
                            boolean modelLoaded = response.optBoolean("model_loaded", false);
                            boolean tesseractReady = response.optBoolean("tesseract_ready", false);
                            boolean ttsReady = response.optBoolean("tts_ready", false);
                            JSONObject stats = response.optJSONObject("stats");
                            int totalDocs = stats != null ? stats.optInt("total_documents", 0) : 0;
                            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTING,
                                    "Server Connected",
                                    String.format("Model: %s | OCR: %s | Docs: %d",
                                            modelLoaded ? "✓" : "✗",
                                            tesseractReady ? "✓" : "✗",
                                            totalDocs));
                            speak("ඕ සී ආර් සේවාදායකය සම්බන්ධයි");  // OCR server connected in Sinhala
                            mainHandler.postDelayed(() ->
                                    speak(String.format("OCR server connected. %d documents processed previously", totalDocs)), 2000);
                            mainHandler.postDelayed(this::startServerCamera, 3000);
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing server response", e);
                        handleServerError("Invalid server response");
                    }
                },
                error -> {
                    Log.e(TAG, "Server connection failed", error);
                    handleServerError("OCR server not found. Check if server is running on " + SERVER_URL);
                });
        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
        requestQueue.add(request);
    }

    private void startServerCamera() {
        String url = SERVER_URL + "/api/camera/start";
        JsonObjectRequest request = new JsonObjectRequest(Request.Method.POST, url, null,
                response -> {
                    try {
                        boolean success = response.getBoolean("success");
                        if (success) {
                            serverCameraActive = true;
                            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                                    "OCR System Ready", "Camera active • Ready for document scanning");
                            speak("කැමරාව සක්‍රීයයි");  // Camera active in Sinhala
                            mainHandler.postDelayed(() -> speak("OCR camera activated successfully"), 2000);
                            // Updated instructions to mention capture
                            updateInstructions("OCR system ready! Say 'START'/'ආරම්භ කරන්න' for continuous scan or 'CAPTURE'/'ග්‍රහණය' for single photo.");
                        } else {
                            handleServerError("Failed to start OCR camera");
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing camera start response", e);
                        handleServerError("Camera activation error");
                    }
                },
                error -> {
                    Log.e(TAG, "Camera start failed", error);
                    handleServerError("Could not activate OCR camera");
                });
        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
        requestQueue.add(request);
    }

    private void handleServerError(String message) {
        serverConnected = false;
        serverCameraActive = false;
        statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                "Connection Failed", message);
        updateInstructions(message);
        speak("සම්බන්ධතා දෝෂයක්");  // Connection error in Sinhala
        mainHandler.postDelayed(() -> speak(message), 2000);
    }

    private void startOCRProcessing() {
        if (!serverConnected) {
            speak("ඕ සී ආර් සේවාදායකය සම්බන්ධ නැත");  // OCR server not connected
            mainHandler.postDelayed(() -> speak("OCR server not connected. Please check connection."), 2000);
            return;
        }
        if (!serverCameraActive) {
            speak("කැමරාව ආරම්භ කරමින්");  // Starting camera
            startServerCamera();
            mainHandler.postDelayed(() -> {
                if (serverCameraActive) {
                    startOCRProcessing();
                } else {
                    speak("කැමරාව සක්‍රීය නැත");  // Camera not active
                }
            }, 3000);
            return;
        }

        if (isProcessing) {
            return;
        }

        isProcessing = true;
        btnStartOCR.setVisibility(View.GONE);
        btnStopOCR.setVisibility(View.VISIBLE);
        btnSpeak.setVisibility(View.VISIBLE);
        btnCapture.setVisibility(View.GONE); // Hide capture button during continuous scan
        statusIndicator.setImageResource(R.drawable.ic_document_scanner);
        statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                "OCR Active", "Scanning documents...");
        updateResults("Point camera at document and hold steady...");
        // Updated instructions for continuous OCR
        updateInstructions("OCR running. Say 'STOP'/'නවතන්න' to end, 'SPEAK'/'කියවන්න' to hear text");
        speak("ඕ සී ආර් පරිලෝකනය ආරම්භයි");  // OCR scanning started
        mainHandler.postDelayed(() -> speak("OCR scanning started. Point camera at document"), 2000);

        startVoiceListening();
        resetPerformanceStats();
        startFrameProcessing();
    }

    private void stopOCRProcessing() {
        if (isProcessing) {
            isProcessing = false;
            btnStartOCR.setVisibility(View.VISIBLE);
            btnStopOCR.setVisibility(View.GONE);
            btnCapture.setVisibility(View.VISIBLE); // Show capture button again
            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                    "OCR System Ready", "Scanning stopped • Ready to start");
            updateStatus("OCR Stopped");
            // Updated instructions after stopping
            updateInstructions("OCR stopped. Say 'START'/'ආරම්භ කරන්න' for continuous scan or 'CAPTURE'/'ග්‍රහණය' for single photo.");
            speak("ඕ සී ආර් නතර කළා");  // OCR stopped
            mainHandler.postDelayed(() -> speak("OCR scanning stopped"), 2000);
            stopVoiceListening();
            showPerformanceStats();
        }
    }

    // NEW METHOD: Capture and process document
    private void captureAndProcessDocument() {
        if (!serverConnected || !serverCameraActive) {
            speak("කැමරාව සම්බන්ධ නැත");  // Camera not connected
            mainHandler.postDelayed(() -> speak("Camera not connected. Please start the system first."), 2000);
            return;
        }

        if (isCapturing) {
            speak("දැනටමත් ග්‍රහණය කරමින්");  // Already capturing
            mainHandler.postDelayed(() -> speak("Already capturing. Please wait."), 1500);
            return;
        }

        if (isProcessing) { // Cannot capture during continuous OCR
            speak("ඕ සී ආර් පරිලෝකනය දැනටමත් පවතී"); // OCR scanning is active
            mainHandler.postDelayed(() -> speak("OCR scanning is active. Stop it first to capture."), 2000);
            return;
        }

        isCapturing = true;

        // Visual feedback
        statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                "Capturing...", "Taking photo for OCR processing");

        // Audio feedback in both languages
        speak("ඡායාරූපය ග්‍රහණය කරමින්");  // Capturing photo
        mainHandler.postDelayed(() -> speak("Capturing photo for OCR"), 1500);

        // Add visual indicator (flash effect)
        documentFeedView.setAlpha(0.3f);
        mainHandler.postDelayed(() -> documentFeedView.setAlpha(1.0f), 200);

        // Request a single frame and process it
        captureFrameAndProcess();
    }

    // NEW METHOD: Capture frame from server and process
    private void captureFrameAndProcess() {
        String url = SERVER_URL + "/api/camera/frame";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        if (response.has("error")) {
                            String errorMsg = response.getString("error");
                            Log.w(TAG, "Capture error: " + errorMsg);
                            handleCaptureError("Camera error: " + errorMsg);
                            return;
                        }

                        String imageBase64 = response.optString("image", "");
                        if (!imageBase64.isEmpty()) {
                            // Display captured frame
                            displayFrame(imageBase64);

                            // Announce capture success
                            speak("ග්‍රහණය සාර්ථකයි");  // Capture successful
                            mainHandler.postDelayed(() -> speak("Photo captured. Processing OCR"), 1500);

                            // Process the captured image
                            mainHandler.postDelayed(() -> {
                                processCapturedDocument(imageBase64);
                            }, 2000);
                        } else {
                            handleCaptureError("Empty frame received");
                        }

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing capture response", e);
                        handleCaptureError("Invalid response from server");
                    }
                },
                error -> {
                    Log.e(TAG, "Capture request error", error);
                    handleCaptureError("Failed to capture photo from server");
                });

        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
        requestQueue.add(request);
    }

    // NEW METHOD: Process captured document
    private void processCapturedDocument(String imageBase64) {
        String url = SERVER_URL + "/api/ocr/process";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("image", imageBase64);

            // Announce processing start
            speak("ඕ සී ආර් සකසමින්");  // OCR processing
            mainHandler.postDelayed(() -> speak("Processing OCR. Please wait"), 1500);

            JsonObjectRequest request = new JsonObjectRequest(Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");

                            if (success) {
                                documentsProcessed++;

                                String docType = response.optString("document_type", "Unknown");
                                String extractedText = response.optString("extracted_text", "");
                                double ocrConf = response.optDouble("ocr_confidence", 0.0);
                                double classConf = response.optDouble("classification_confidence", 0.0);
                                double qualityScore = response.optDouble("quality_score", 0.0);
                                double processingTime = response.optDouble("processing_time", 0.0);
                                int textLength = response.optInt("text_length", 0);

                                if (!extractedText.isEmpty()) {
                                    successfulOCR++;
                                    lastExtractedText = extractedText;
                                    lastDocumentType = docType;
                                    lastOCRConfidence = ocrConf;
                                    lastClassificationConfidence = classConf;

                                    String resultMessage = String.format(
                                            "📸 CAPTURED DOCUMENT\n" +
                                                    "📄 Type: %s\n" +
                                                    "📝 Extracted Text (%d chars):\n%s\n\n" +
                                                    "🎯 Classification: %.1f%%\n" +
                                                    "🔍 OCR Confidence: %.1f%%\n" +
                                                    "📊 Quality: %.1f%%\n" +
                                                    "⚡ Processing Time: %.0fms",
                                            docType,
                                            textLength,
                                            extractedText.length() > 200 ?
                                                    extractedText.substring(0, 200) + "..." : extractedText,
                                            classConf * 100,
                                            ocrConf * 100,
                                            qualityScore * 100,
                                            processingTime * 1000
                                    );

                                    mainHandler.post(() -> {
                                        updateResults(resultMessage);
                                        updateOCRConfidence(ocrConf, classConf);
                                        updatePerformanceDisplay();

                                        statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                                                "Capture Complete",
                                                String.format("Found: %s (%.1f%% confidence)", docType, classConf * 100));
                                    });

                                    // Announce results in both languages
                                    speak("ලේඛනයක් හමු වුණා");  // Document found
                                    mainHandler.postDelayed(() ->
                                            speak(String.format("Document detected: %s with %.0f percent confidence",
                                                    docType, classConf * 100)), 2000);

                                    // Auto-read extracted text after announcement
                                    mainHandler.postDelayed(() -> {
                                        speak("නිස්සාරණය කළ පෙළ කියවමින්");  // Reading extracted text
                                        mainHandler.postDelayed(this::speakExtractedText, 1500);
                                    }, 4000);

                                } else {
                                    handleCaptureError("No text detected in captured image");
                                }
                            } else {
                                String error = response.optString("error", "Processing failed");
                                handleCaptureError(error);
                            }

                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing OCR response", e);
                            handleCaptureError("Invalid OCR response");
                        } finally {
                            isCapturing = false;
                        }
                    },
                    error -> {
                        Log.e(TAG, "OCR processing error", error);
                        handleCaptureError("OCR processing failed");
                    });

            request.setRetryPolicy(new DefaultRetryPolicy(15000, 0, 1.0f));
            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating OCR request", e);
            handleCaptureError("Failed to create OCR request");
        }
    }

    // NEW METHOD: Handle capture errors
    private void handleCaptureError(String errorMessage) {
        isCapturing = false;

        mainHandler.post(() -> {
            updateResults("❌ Capture Error: " + errorMessage);
            statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                    "Capture Failed", errorMessage);
        });

        speak("ග්‍රහණය අසාර්ථකයි");  // Capture failed
        mainHandler.postDelayed(() -> speak("Capture failed: " + errorMessage), 1500);
    }


    private void startFrameProcessing() {
        executorService.execute(this::frameProcessingLoop);
    }

    private void frameProcessingLoop() {
        while (isProcessing) {
            try {
                if (System.currentTimeMillis() - lastFrameRequestTime > FRAME_REQUEST_INTERVAL) {
                    requestFrameFromServer();
                    lastFrameRequestTime = System.currentTimeMillis();
                }
                Thread.sleep(100);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    private void requestFrameFromServer() {
        if (!serverCameraActive || !isProcessing) {
            return;
        }
        String url = SERVER_URL + "/api/camera/frame";
        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        totalFramesReceived++;
                        if (response.has("error")) {
                            String errorMsg = response.getString("error");
                            Log.w(TAG, "Server error: " + errorMsg);
                            if (errorMsg.contains("Camera not active")) {
                                serverCameraActive = false;
                                mainHandler.postDelayed(this::startServerCamera, 2000);
                            }
                            return;
                        }
                        String imageBase64 = response.optString("image", "");
                        if (!imageBase64.isEmpty()) {
                            displayFrame(imageBase64);
                            // Process document at intervals
                            if (System.currentTimeMillis() - lastProcessingTime > PROCESSING_INTERVAL) {
                                processDocument(imageBase64);
                                lastProcessingTime = System.currentTimeMillis();
                            }
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing frame response", e);
                    }
                },
                error -> {
                    Log.e(TAG, "Frame request error", error);
                    if (error instanceof com.android.volley.ServerError) {
                        serverCameraActive = false;
                        mainHandler.postDelayed(this::testServerConnection, 3000);
                    }
                });
        request.setRetryPolicy(new DefaultRetryPolicy(2000, 1, 1.0f));
        requestQueue.add(request);
    }

    private void displayFrame(String imageBase64) {
        try {
            byte[] imageBytes = Base64.decode(imageBase64, Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);
            if (bitmap != null) {
                mainHandler.post(() -> {
                    documentFeedView.setImageBitmap(bitmap);
                    findViewById(R.id.noFeedMessage).setVisibility(View.GONE);
                });
            }
        } catch (Exception e) {
            Log.e(TAG, "Error displaying frame", e);
        }
    }

    private void processDocument(String imageBase64) {
        String url = SERVER_URL + "/api/ocr/process";
        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("image", imageBase64);
            JsonObjectRequest request = new JsonObjectRequest(Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");
                            if (success) {
                                documentsProcessed++;
                                String docType = response.optString("document_type", "Unknown");
                                String extractedText = response.optString("extracted_text", "");
                                double ocrConf = response.optDouble("ocr_confidence", 0.0);
                                double classConf = response.optDouble("classification_confidence", 0.0);
                                double qualityScore = response.optDouble("quality_score", 0.0);
                                double processingTime = response.optDouble("processing_time", 0.0);
                                int textLength = response.optInt("text_length", 0);
                                if (!extractedText.isEmpty()) {
                                    successfulOCR++;
                                    lastExtractedText = extractedText;
                                    lastDocumentType = docType;
                                    lastOCRConfidence = ocrConf;
                                    lastClassificationConfidence = classConf;
                                    String resultMessage = String.format(
                                            "📄 Document Type: %s\n" +
                                                    "📝 Extracted Text (%d chars):\n%s\n" +
                                                    "🎯 Classification: %.1f%%\n" +
                                                    "🔍 OCR Confidence: %.1f%%\n" +
                                                    "📊 Quality: %.1f%%\n" +
                                                    "⚡ Time: %.0fms",
                                            docType,
                                            textLength,
                                            extractedText.length() > 200 ?
                                                    extractedText.substring(0, 200) + "..." : extractedText,
                                            classConf * 100,
                                            ocrConf * 100,
                                            qualityScore * 100,
                                            processingTime * 1000
                                    );
                                    mainHandler.post(() -> {
                                        updateResults(resultMessage);
                                        updateOCRConfidence(ocrConf, classConf);
                                        updatePerformanceDisplay();
                                    });
                                    // Announce document detection in both languages
                                    speak("ලේඛනයක් හමු වුණා");  // Document found
                                    mainHandler.postDelayed(() ->
                                            speak("Document detected: " + docType), 2000);
                                    // Auto-read the extracted text if it's short (less than 50 chars)
                                    if (extractedText.length() < 50 && !isReadingText) {
                                        mainHandler.postDelayed(this::speakExtractedText, 4000);
                                    }
                                } else {
                                    mainHandler.post(() -> {
                                        updateResults("⚠️ No text detected. Ensure document is clear and well-lit");
                                        speak("පෙළ හමු නොවුණා");  // No text found
                                    });
                                }
                            } else {
                                String error = response.optString("error", "Processing failed");
                                mainHandler.post(() -> {
                                    updateResults("❌ Error: " + error);
                                });
                            }
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing OCR response", e);
                        }
                    },
                    error -> {
                        Log.e(TAG, "OCR processing error", error);
                        mainHandler.post(() -> {
                            updateResults("⚠️ Processing error - retrying...");
                        });
                    });
            request.setRetryPolicy(new DefaultRetryPolicy(15000, 0, 1.0f));
            requestQueue.add(request);
        } catch (JSONException e) {
            Log.e(TAG, "Error creating OCR request", e);
        }
    }

    private void speakExtractedText() {
        if (lastExtractedText.isEmpty()) {
            speak("පෙළ නිස්සාරණය කර නැත");  // No text extracted
            mainHandler.postDelayed(() -> speak("No text has been extracted yet"), 1500);
            return;
        }
        isReadingText = true;
        speak("නිස්සාරණය කළ පෙළ කියවමින්");  // Reading extracted text
        mainHandler.postDelayed(() -> {
            // Detect if text contains Sinhala characters
            boolean hasSinhala = lastExtractedText.matches(".*[\\u0D80-\\u0DFF].*");
            Locale locale = hasSinhala ? new Locale("si", "LK") : Locale.ENGLISH;
            // Announce language
            if (hasSinhala) {
                speak("සිංහල පෙළ", new Locale("si", "LK"));
            } else {
                speak("English text", Locale.ENGLISH);
            }
            // Read the actual text after a short delay
            mainHandler.postDelayed(() -> {
                speak(lastExtractedText, locale);
                mainHandler.postDelayed(() -> isReadingText = false, 2000);
            }, 2000);
        }, 1500);
    }

    private void startVoiceListening() {
        if (!isListening) {
            isListening = true;
            speechRecognizer.startListening(speechRecognizerIntent);
        }
    }

    private void stopVoiceListening() {
        if (isListening) {
            isListening = false;
            speechRecognizer.stopListening();
        }
    }

    // UPDATED METHOD: Process voice commands including capture
    private void processVoiceCommand(String command) {
        String lowerCommand = command.toLowerCase().trim();
        Log.d(TAG, "Voice command received: " + command);

        // Capture commands - English
        if (lowerCommand.contains("capture") || lowerCommand.contains("take photo") ||
                lowerCommand.contains("take picture") || lowerCommand.contains("snap")) {
            captureAndProcessDocument();
        }
        // Capture commands - Sinhala: ග්‍රහණය, ඡායාරූපය, ගන්න
        else if (lowerCommand.contains("ග්‍රහණය") || lowerCommand.contains("ඡායාරූපය") ||
                lowerCommand.contains("ගන්න")) {
            captureAndProcessDocument();
        }
        // Start commands - English
        else if ((lowerCommand.contains("start") || lowerCommand.contains("begin")) && !isProcessing) {
            startOCRProcessing();
        }
        // Start commands - Sinhala: ආරම්භ, පටන්
        else if ((lowerCommand.contains("ආරම්භ") || lowerCommand.contains("පටන්")) && !isProcessing) {
            startOCRProcessing();
        }
        // Stop commands - English
        else if ((lowerCommand.contains("stop") || lowerCommand.contains("end")) && isProcessing) {
            stopOCRProcessing();
        }
        // Stop commands - Sinhala: නවතන්න, නවත, නතර
        else if ((lowerCommand.contains("නවතන්න") || lowerCommand.contains("නවත") ||
                lowerCommand.contains("නතර")) && isProcessing) {
            stopOCRProcessing();
        }
        // Speak/Read commands - English
        else if (lowerCommand.contains("speak") || lowerCommand.contains("read")) {
            speakExtractedText();
        }
        // Speak/Read commands - Sinhala: කියවන්න, කියවන, කියන්න
        else if (lowerCommand.contains("කියවන්න") || lowerCommand.contains("කියවන") ||
                lowerCommand.contains("කියන්න")) {
            speakExtractedText();
        }
        // Back commands - English
        else if (lowerCommand.contains("back") || lowerCommand.contains("return") ||
                lowerCommand.contains("exit")) {
            speak("ආපසු යනවා");  // Going back
            mainHandler.postDelayed(() -> speak("Going back to main menu"), 1500);
            mainHandler.postDelayed(this::finish, 3000);
        }
        // Back commands - Sinhala: ආපසු, ආපස්සට, පිටවන්න
        else if (lowerCommand.contains("ආපසු") || lowerCommand.contains("ආපස්සට") ||
                lowerCommand.contains("පිටවන්න")) {
            speak("ආපසු යනවා");  // Going back
            mainHandler.postDelayed(this::finish, 2000);
        }
        // Help - provide available commands
        else {
            if (isProcessing) {
                speak("නවතන්න, කියවන්න, හෝ ආපසු යන්න කියන්න");  // Say stop, read, or back
                mainHandler.postDelayed(() ->
                        speak("Commands available: stop, speak, or back"), 2000);
            } else {
                speak("ආරම්භ කරන්න, ග්‍රහණය, කියවන්න, හෝ ආපසු යන්න කියන්න"); // Added capture
                mainHandler.postDelayed(() ->
                        speak("Commands available: start, capture, speak, or back"), 2000); // Added capture
            }
        }
    }


    private void resetPerformanceStats() {
        totalFramesReceived = 0;
        documentsProcessed = 0;
        successfulOCR = 0;
        lastProcessingTime = 0;
        lastFrameRequestTime = 0;
    }

    private void updatePerformanceDisplay() {
        if (performanceText == null) return;
        float successRate = documentsProcessed > 0 ?
                (float) successfulOCR / documentsProcessed * 100 : 0;
        String performance = String.format(
                "📊 Frames: %d | Processed: %d | Success: %d (%.1f%%)",
                totalFramesReceived, documentsProcessed, successfulOCR, successRate
        );
        performanceText.setText(performance);
    }

    private void updateOCRConfidence(double ocrConf, double classConf) {
        if (ocrConfidenceText == null) return;
        String confidence = String.format(
                "OCR: %.1f%% | Classification: %.1f%%",
                ocrConf * 100, classConf * 100
        );
        ocrConfidenceText.setText(confidence);
    }

    private void showPerformanceStats() {
        String statsMessage = String.format(
                "OCR Performance: Received %d frames, processed %d documents, " +
                        "%d successful extractions (%.1f%% success rate).",
                totalFramesReceived, documentsProcessed, successfulOCR,
                documentsProcessed > 0 ? (float) successfulOCR / documentsProcessed * 100 : 0
        );
        updateResults("📊 " + statsMessage);
    }

    private void updateStatus(String message) {
        statusText.setText(message);
        statusText.setContentDescription(message);
    }

    private void updateResults(String results) {
        resultsText.setText(results);
        resultsText.setContentDescription("OCR result: " + results);
    }

    private void updateInstructions(String instructions) {
        instructionsText.setText(instructions);
        instructionsText.setContentDescription("Instructions: " + instructions);
    }

    private void speak(String text) {
        speak(text, null);
    }

    private void speak(String text, Locale locale) {
        if (ttsEngine != null && isTtsReady) {
            Locale targetLocale = locale != null ? locale : Locale.ENGLISH;
            if (targetLocale != ttsEngine.getLanguage()) {
                int result = ttsEngine.setLanguage(targetLocale);
                if (result == TextToSpeech.LANG_MISSING_DATA ||
                        result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.w(TAG, "Language not supported: " + targetLocale + ", using English");
                    ttsEngine.setLanguage(Locale.ENGLISH);
                }
            }
            ttsEngine.speak(text, TextToSpeech.QUEUE_ADD, null, "OCR_UTTERANCE");
        }
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches != null && !matches.isEmpty()) {
            String recognizedText = matches.get(0);
            processVoiceCommand(recognizedText);
        }
        if (isListening && isProcessing) {
            mainHandler.postDelayed(() -> {
                if (isListening && isProcessing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override
    public void onError(int error) {
        if (error != SpeechRecognizer.ERROR_NO_MATCH && isListening) {
            mainHandler.postDelayed(() -> {
                if (isListening && isProcessing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override public void onReadyForSpeech(Bundle params) {}
    @Override public void onBeginningOfSpeech() {}
    @Override public void onRmsChanged(float rmsdB) {}
    @Override public void onBufferReceived(byte[] buffer) {}
    @Override public void onEndOfSpeech() {}
    @Override public void onPartialResults(Bundle partialResults) {}
    @Override public void onEvent(int eventType, Bundle params) {}

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            // Try Sinhala first
            int sinhalaResult = ttsEngine.setLanguage(new Locale("si", "LK"));
            if (sinhalaResult == TextToSpeech.LANG_MISSING_DATA ||
                    sinhalaResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.w(TAG, "Sinhala TTS not available, using English");
                ttsEngine.setLanguage(Locale.US);
            }
            isTtsReady = true;
            mainHandler.postDelayed(() -> {
                if (!isProcessing) {
                    startVoiceListening();
                }
            }, 1000);
        } else {
            updateStatus("TTS Language not supported");
            speak("Text to speech initialization failed");
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isProcessing) {
            stopOCRProcessing();
        }
        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }
        if (speechRecognizer != null) {
            speechRecognizer.destroy();
        }
        if (executorService != null) {
            executorService.shutdown();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopVoiceListening();
        if (isProcessing) {
            stopOCRProcessing();
        }
        // Stop TTS when pausing
        if (ttsEngine != null && ttsEngine.isSpeaking()) {
            ttsEngine.stop();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (serverConnected && !isProcessing && !isCapturing) { // Added isCapturing check
            testServerConnection();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == AUDIO_PERMISSION_REQUEST) {
            boolean allPermissionsGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allPermissionsGranted = false;
                    break;
                }
            }
            if (allPermissionsGranted) {
                speak("ශ්‍රව්‍ය අවසරය ලැබුණා");  // Audio permission granted
                mainHandler.postDelayed(() -> speak("Audio permission granted. OCR system ready."), 2000);
            } else {
                speak("මයික්‍රෆෝන අවසරය අවශ්‍යයි");  // Microphone permission required
                mainHandler.postDelayed(() -> speak("Microphone permission is required for voice commands."), 2000);
                mainHandler.postDelayed(this::finish, 4000);
            }
        }
    }
}