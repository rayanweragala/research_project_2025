package com.research.blindassistant;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.graphics.Bitmap;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Base64;
import android.util.Log;
import android.view.View;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONArray;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.text.SimpleDateFormat;
import java.util.Date;

public class SinhalaOCRActivity extends AppCompatActivity implements TextToSpeech.OnInitListener, RecognitionListener {

    private static final String TAG = "SinhalaOCRActivity";
    private static final String OCR_SERVER_URL = "http://10.72.250.126:5002";

    // UI Components
    private TextView statusText, instructionsText, extractedTextView, confidenceText, processingTimeText;
    private Button btnCapture, btnReadText, btnCancel, btnStartOver, btnSaveResult;
    private ImageView documentPreview, qualityIndicator, statusIndicator;
    private ProgressBar processingProgress;
    private ScrollView textScrollView;

    // Services
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private ToneGenerator toneGenerator;
    private RequestQueue requestQueue;
    private Handler mainHandler;
    private Handler backgroundHandler;
    private HandlerThread backgroundThread;

    // State variables
    private boolean isListening = false;
    private boolean isTtsReady = false;
    private boolean isProcessing = false;
    private OCRState currentState = OCRState.READY_TO_CAPTURE;

    // OCR Results
    private String extractedText = "";
    private String documentType = "";
    private double ocrConfidence = 0.0;
    private double classificationConfidence = 0.0;
    private double qualityScore = 0.0;
    private double processingTime = 0.0;
    private List<OCRResult> ocrHistory = new ArrayList<>();

    // Audio feedback tones
    private static final int TONE_CAPTURE_SUCCESS = ToneGenerator.TONE_PROP_BEEP2;
    private static final int TONE_PROCESSING = ToneGenerator.TONE_DTMF_1;
    private static final int TONE_COMPLETE = ToneGenerator.TONE_CDMA_CONFIRM;
    private static final int TONE_ERROR = ToneGenerator.TONE_CDMA_ABBR_ALERT;

    private enum OCRState {
        READY_TO_CAPTURE,
        CAPTURING,
        PROCESSING,
        RESULTS_AVAILABLE,
        ERROR
    }

    // OCR Result data class
    public static class OCRResult {
        public String timestamp;
        public String documentType;
        public String extractedText;
        public double ocrConfidence;
        public double classificationConfidence;
        public double qualityScore;
        public double processingTime;
        public int textLength;
        public boolean success;

        public OCRResult(String documentType, String text, double ocrConf, double classConf,
                         double quality, double procTime, boolean success) {
            this.timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date());
            this.documentType = documentType;
            this.extractedText = text;
            this.ocrConfidence = ocrConf;
            this.classificationConfidence = classConf;
            this.qualityScore = quality;
            this.processingTime = procTime;
            this.textLength = text != null ? text.length() : 0;
            this.success = success;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_sinhala_ocr);

        initializeComponents();
        setupServices();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        mainHandler = new Handler();
        backgroundThread = new HandlerThread("OCRProcessor");
        backgroundThread.start();
        backgroundHandler = new Handler(backgroundThread.getLooper());

        requestQueue = Volley.newRequestQueue(this);
        ttsEngine = new TextToSpeech(this, this);

        try {
            toneGenerator = new ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80);
        } catch (RuntimeException e) {
            Log.w(TAG, "Could not create ToneGenerator", e);
        }

        checkOCRServerHealth();
    }

    private void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        instructionsText = findViewById(R.id.instructionsText);
        extractedTextView = findViewById(R.id.extractedTextView);
        confidenceText = findViewById(R.id.confidenceText);
        processingTimeText = findViewById(R.id.processingTimeText);

        btnCapture = findViewById(R.id.btnCapture);
        btnReadText = findViewById(R.id.btnReadText);
        btnCancel = findViewById(R.id.btnCancel);
        btnStartOver = findViewById(R.id.btnStartOver);
        btnSaveResult = findViewById(R.id.btnSaveResult);

        documentPreview = findViewById(R.id.documentPreview);
        qualityIndicator = findViewById(R.id.qualityIndicator);
        statusIndicator = findViewById(R.id.statusIndicator);
        processingProgress = findViewById(R.id.processingProgress);
        textScrollView = findViewById(R.id.textScrollView);

        updateUIForState(OCRState.READY_TO_CAPTURE);
    }

    private void setupServices() {
        // Initialize any additional services if needed
    }

    private void setupVoiceRecognition() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Log.e(TAG, "Speech recognition not available on this device");
            speak("Speech recognition is not available on this device");
            return;
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(this);

        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, getPackageName());
    }

    private void setupButtons() {
        btnCapture.setOnClickListener(v -> {
            if (currentState == OCRState.READY_TO_CAPTURE) {
                speak("Capturing document for OCR processing");
                captureDocumentFromCamera();
            }
        });

        btnReadText.setOnClickListener(v -> {
            if (currentState == OCRState.RESULTS_AVAILABLE && !extractedText.isEmpty()) {
                speak("Reading extracted text");
                readExtractedText();
            } else {
                speak("No text available to read");
            }
        });

        btnSaveResult.setOnClickListener(v -> {
            if (currentState == OCRState.RESULTS_AVAILABLE) {
                saveOCRResult();
            }
        });

        btnStartOver.setOnClickListener(v -> {
            speak("Starting over");
            resetToInitialState();
        });

        btnCancel.setOnClickListener(v -> {
            speak("Canceling OCR processing");
            finishActivity();
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnCapture, btnReadText, btnSaveResult, btnStartOver, btnCancel};
        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("Button: " + buttonText);
                return true;
            });
        }
    }

    @SuppressLint("SetTextI18n")
    private void updateUIForState(OCRState newState) {
        currentState = newState;

        switch (newState) {
            case READY_TO_CAPTURE:
                statusText.setText("Ready to capture document");
                instructionsText.setText("Press the capture button to take a photo of the document for OCR processing");
                statusIndicator.setImageResource(R.drawable.ic_ready);
                processingProgress.setVisibility(View.GONE);
                btnCapture.setVisibility(View.VISIBLE);
                btnReadText.setVisibility(View.GONE);
                btnSaveResult.setVisibility(View.GONE);
                btnStartOver.setVisibility(View.GONE);
                qualityIndicator.setVisibility(View.GONE);
                break;

            case CAPTURING:
                statusText.setText("Capturing document");
                instructionsText.setText("Hold the device steady while capturing the document");
                statusIndicator.setImageResource(R.drawable.ic_capturing);
                btnCapture.setVisibility(View.GONE);
                break;

            case PROCESSING:
                statusText.setText("Processing document with AI OCR");
                instructionsText.setText("Please wait while the Sinhala OCR system processes your document...");
                statusIndicator.setImageResource(R.drawable.ic_processing);
                processingProgress.setVisibility(View.VISIBLE);
                processingProgress.setIndeterminate(true);
                qualityIndicator.setVisibility(View.VISIBLE);
                break;

            case RESULTS_AVAILABLE:
                statusText.setText("OCR processing completed!");
                instructionsText.setText("Text extracted successfully. You can read the text or save the result.");
                statusIndicator.setImageResource(R.drawable.ic_success);
                processingProgress.setVisibility(View.GONE);
                btnReadText.setVisibility(View.VISIBLE);
                btnSaveResult.setVisibility(View.VISIBLE);
                btnStartOver.setVisibility(View.VISIBLE);
                textScrollView.setVisibility(View.VISIBLE);
                updateResultsDisplay();
                break;

            case ERROR:
                statusText.setText("OCR processing failed");
                instructionsText.setText("An error occurred during processing. Press 'Start Over' to try again.");
                statusIndicator.setImageResource(R.drawable.ic_error);
                processingProgress.setVisibility(View.GONE);
                btnStartOver.setVisibility(View.VISIBLE);
                break;
        }
    }

    private void checkOCRServerHealth() {
        String url = OCR_SERVER_URL + "/api/ocr/health";

        JsonObjectRequest healthRequest = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        String status = response.getString("status");
                        boolean modelLoaded = response.getBoolean("model_loaded");
                        boolean tesseractReady = response.getBoolean("tesseract_ready");

                        if ("healthy".equals(status) && (modelLoaded || tesseractReady)) {
                            speak("Sinhala OCR server is ready and operational");
                            Log.d(TAG, "OCR server health check passed");
                        } else {
                            speak("OCR server is running but some components may be unavailable");
                            Log.w(TAG, "OCR server partially available");
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing health response", e);
                        speak("Connected to OCR server");
                    }
                },
                error -> {
                    Log.e(TAG, "OCR server health check failed", error);
                    speak("Warning: OCR server may not be available. Check your network connection.");
                    updateUIForState(OCRState.ERROR);
                }
        );

        healthRequest.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1f));
        requestQueue.add(healthRequest);
    }

    private void captureDocumentFromCamera() {
        updateUIForState(OCRState.CAPTURING);
        playTone(TONE_CAPTURE_SUCCESS);

        // Simulate camera capture - in real implementation, this would use camera API
        // For now, we'll use a mock image capture
        mainHandler.postDelayed(() -> {
            // Mock bitmap creation - replace with actual camera capture
            Bitmap mockDocument = createMockDocumentBitmap();
            if (mockDocument != null) {
                processDocumentImage(mockDocument);
            } else {
                onProcessingError("Failed to capture document image");
            }
        }, 1000);
    }

    private Bitmap createMockDocumentBitmap() {
        // Create a mock bitmap for testing - replace with actual camera implementation
        try {
            Bitmap mockBitmap = Bitmap.createBitmap(640, 480, Bitmap.Config.RGB_565);
            // In real implementation, this would be the captured camera frame
            return mockBitmap;
        } catch (Exception e) {
            Log.e(TAG, "Error creating mock bitmap", e);
            return null;
        }
    }

    private void processDocumentImage(Bitmap documentImage) {
        updateUIForState(OCRState.PROCESSING);
        playTone(TONE_PROCESSING);
        isProcessing = true;

        backgroundHandler.post(() -> {
            try {
                // Convert bitmap to base64
                String imageBase64 = bitmapToBase64(documentImage);
                if (imageBase64 == null) {
                    runOnUiThread(() -> onProcessingError("Failed to process image data"));
                    return;
                }

                runOnUiThread(() -> {
                    documentPreview.setImageBitmap(documentImage);
                    documentPreview.setVisibility(View.VISIBLE);
                });

                // Send to OCR server
                sendOCRRequest(imageBase64);

            } catch (Exception e) {
                Log.e(TAG, "Error processing document image", e);
                runOnUiThread(() -> onProcessingError("Image processing error: " + e.getMessage()));
            }
        });
    }

    private String bitmapToBase64(Bitmap bitmap) {
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.JPEG, 85, baos);
            byte[] imageBytes = baos.toByteArray();
            baos.close();
            return Base64.encodeToString(imageBytes, Base64.NO_WRAP);
        } catch (Exception e) {
            Log.e(TAG, "Error converting bitmap to base64", e);
            return null;
        }
    }

    private void sendOCRRequest(String imageBase64) {
        String url = OCR_SERVER_URL + "/api/ocr/process";

        JSONObject requestData = new JSONObject();
        try {
            requestData.put("image", imageBase64);
        } catch (JSONException e) {
            onProcessingError("Failed to create request data");
            return;
        }

        JsonObjectRequest ocrRequest = new JsonObjectRequest(
                Request.Method.POST, url, requestData,
                this::handleOCRResponse,
                error -> {
                    Log.e(TAG, "OCR request failed", error);
                    String errorMsg = "Network error occurred";
                    if (error.networkResponse != null) {
                        errorMsg = "Server error: " + error.networkResponse.statusCode;
                    }
                    onProcessingError(errorMsg);
                }
        );

        ocrRequest.setRetryPolicy(new DefaultRetryPolicy(30000, 1, 1f));
        requestQueue.add(ocrRequest);

        Log.d(TAG, "OCR request sent to server");
    }

    private void handleOCRResponse(JSONObject response) {
        Log.d(TAG, "OCR response received: " + response.toString());

        try {
            boolean success = response.getBoolean("success");

            if (success) {
                // Extract OCR results
                documentType = response.optString("document_type", "Unknown");
                extractedText = response.optString("extracted_text", "");
                ocrConfidence = response.optDouble("ocr_confidence", 0.0);
                classificationConfidence = response.optDouble("classification_confidence", 0.0);
                qualityScore = response.optDouble("quality_score", 0.0);
                processingTime = response.optDouble("processing_time", 0.0);

                // Log the successful OCR
                logOCRResult(true, "OCR processing completed successfully");

                if (!extractedText.isEmpty()) {
                    playTone(TONE_COMPLETE);
                    speak(String.format("OCR completed! Extracted %d characters from %s document with %.1f%% confidence.",
                            extractedText.length(), documentType, ocrConfidence * 100));
                    updateUIForState(OCRState.RESULTS_AVAILABLE);
                } else {
                    speak("OCR completed but no text was detected in the document");
                    logOCRResult(false, "No text detected in document");
                    updateUIForState(OCRState.ERROR);
                }

            } else {
                String error = response.optString("error", "Unknown error occurred");
                onProcessingError("OCR failed: " + error);
            }

        } catch (JSONException e) {
            Log.e(TAG, "Error parsing OCR response", e);
            onProcessingError("Failed to parse server response");
        }

        isProcessing = false;
    }

    private void onProcessingError(String error) {
        Log.e(TAG, "Processing error: " + error);
        playTone(TONE_ERROR);
        speak("Error occurred: " + error);
        logOCRResult(false, error);
        updateUIForState(OCRState.ERROR);
        isProcessing = false;
    }

    @SuppressLint("SetTextI18n")
    private void updateResultsDisplay() {
        // Display extracted text
        extractedTextView.setText(extractedText);
        extractedTextView.setVisibility(View.VISIBLE);

        // Display confidence and processing info
        String confidenceInfo = String.format(Locale.getDefault(),
                "Document: %s\nOCR Confidence: %.1f%%\nClassification: %.1f%%\nQuality: %.1f%%",
                documentType, ocrConfidence * 100, classificationConfidence * 100, qualityScore * 100);
        confidenceText.setText(confidenceInfo);
        confidenceText.setVisibility(View.VISIBLE);

        String processingInfo = String.format(Locale.getDefault(),
                "Processing Time: %.2f seconds\nText Length: %d characters",
                processingTime, extractedText.length());
        processingTimeText.setText(processingInfo);
        processingTimeText.setVisibility(View.VISIBLE);

        // Update quality indicator
        updateQualityIndicator(qualityScore);
    }

    private void updateQualityIndicator(double quality) {
        if (quality >= 0.8) {
            qualityIndicator.setImageResource(R.drawable.ic_quality_good);
        } else if (quality >= 0.6) {
            qualityIndicator.setImageResource(R.drawable.ic_quality_medium);
        } else {
            qualityIndicator.setImageResource(R.drawable.ic_quality_poor);
        }
        qualityIndicator.setVisibility(View.VISIBLE);
    }

    private void readExtractedText() {
        if (!extractedText.isEmpty()) {
            speak("Reading extracted text: " + extractedText);
        } else {
            speak("No text available to read");
        }
    }

    private void saveOCRResult() {
        OCRResult result = new OCRResult(documentType, extractedText, ocrConfidence,
                classificationConfidence, qualityScore, processingTime, true);
        ocrHistory.add(result);

        speak(String.format("Result saved! You have processed %d documents in this session.", ocrHistory.size()));
        logOCRResult(true, "OCR result saved successfully");
    }

    private void logOCRResult(boolean success, String message) {
        String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date());
        String logEntry = String.format(Locale.getDefault(),
                "[%s] OCR %s - %s | Document: %s | Confidence: %.1f%% | Quality: %.1f%% | Time: %.2fs",
                timestamp, success ? "SUCCESS" : "FAILED", message, documentType,
                ocrConfidence * 100, qualityScore * 100, processingTime);

        Log.i(TAG, logEntry);

        // Store in OCR history
        if (success) {
            OCRResult result = new OCRResult(documentType, extractedText, ocrConfidence,
                    classificationConfidence, qualityScore, processingTime, success);
            ocrHistory.add(result);
        }
    }

    private void resetToInitialState() {
        Log.d(TAG, "Resetting to initial state");

        stopVoiceListening();
        isProcessing = false;

        // Clear previous results
        extractedText = "";
        documentType = "";
        ocrConfidence = 0.0;
        classificationConfidence = 0.0;
        qualityScore = 0.0;
        processingTime = 0.0;

        // Reset UI
        extractedTextView.setText("");
        extractedTextView.setVisibility(View.GONE);
        confidenceText.setVisibility(View.GONE);
        processingTimeText.setVisibility(View.GONE);
        textScrollView.setVisibility(View.GONE);
        documentPreview.setVisibility(View.GONE);

        updateUIForState(OCRState.READY_TO_CAPTURE);

        mainHandler.postDelayed(this::startVoiceListening, 1000);
    }

    // Voice recognition methods
    private void startVoiceListening() {
        if (!isTtsReady || speechRecognizer == null || isProcessing) {
            return;
        }

        if (!isListening) {
            isListening = true;
            try {
                speechRecognizer.startListening(speechRecognizerIntent);
                Log.d(TAG, "Voice listening started");
            } catch (Exception e) {
                Log.e(TAG, "Error starting speech recognition", e);
                isListening = false;
            }
        }
    }

    private void stopVoiceListening() {
        if (isListening && speechRecognizer != null) {
            isListening = false;
            try {
                speechRecognizer.stopListening();
            } catch (Exception e) {
                Log.e(TAG, "Error stopping speech recognition", e);
            }
        }
    }

    private void speak(String text) {
        if (ttsEngine != null && isTtsReady) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "utterance_id");
            Log.d(TAG, "TTS: " + text);
        } else {
            Log.w(TAG, "TTS not ready, message: " + text);
        }
    }

    private void playTone(int toneType) {
        if (toneGenerator != null) {
            try {
                toneGenerator.startTone(toneType, 200);
            } catch (Exception e) {
                Log.e(TAG, "Error playing tone", e);
            }
        }
    }

    private void finishActivity() {
        Intent resultIntent = new Intent();
        resultIntent.putExtra("ocr_sessions", ocrHistory.size());
        resultIntent.putExtra("total_characters", getTotalCharactersProcessed());
        setResult(RESULT_OK, resultIntent);
        finish();
    }

    private int getTotalCharactersProcessed() {
        int total = 0;
        for (OCRResult result : ocrHistory) {
            total += result.textLength;
        }
        return total;
    }

    // TextToSpeech.OnInitListener
    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.getDefault());
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                ttsEngine.setLanguage(Locale.ENGLISH);
            }
            isTtsReady = true;
            speak("Sinhala OCR system ready. Press capture to scan a document.");
            mainHandler.postDelayed(this::startVoiceListening, 2000);
        } else {
            Log.e(TAG, "TTS initialization failed");
        }
    }

    // RecognitionListener methods
    @Override
    public void onResults(Bundle results) {
        isListening = false;
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);

        if (matches != null && !matches.isEmpty()) {
            String spokenText = matches.get(0).trim().toLowerCase();
            processVoiceCommand(spokenText);
        }
    }

    private void processVoiceCommand(String command) {
        Log.d(TAG, "Processing voice command: " + command);

        if (command.contains("capture") || command.contains("scan")) {
            if (currentState == OCRState.READY_TO_CAPTURE) {
                captureDocumentFromCamera();
            }
        } else if (command.contains("read") || command.contains("speak")) {
            if (currentState == OCRState.RESULTS_AVAILABLE) {
                readExtractedText();
            }
        } else if (command.contains("save")) {
            if (currentState == OCRState.RESULTS_AVAILABLE) {
                saveOCRResult();
            }
        } else if (command.contains("start over") || command.contains("reset")) {
            resetToInitialState();
        } else if (command.contains("cancel") || command.contains("exit")) {
            finishActivity();
        } else {
            // Continue listening for valid commands
            mainHandler.postDelayed(this::startVoiceListening, 1000);
        }
    }

    @Override
    public void onError(int error) {
        isListening = false;
        Log.e(TAG, "Speech recognition error: " + error);

        // Restart listening after a delay unless we're processing
        if (!isProcessing) {
            mainHandler.postDelayed(this::startVoiceListening, 2000);
        }
    }

    // Other RecognitionListener methods (minimal implementation)
    @Override public void onReadyForSpeech(Bundle params) { }
    @Override public void onBeginningOfSpeech() { }
    @Override public void onRmsChanged(float rmsdB) { }
    @Override public void onBufferReceived(byte[] buffer) { }
    @Override public void onEndOfSpeech() { isListening = false; }
    @Override public void onPartialResults(Bundle partialResults) { }
    @Override public void onEvent(int eventType, Bundle params) { }

    @Override
    protected void onDestroy() {
        super.onDestroy();

        stopVoiceListening();

        if (backgroundHandler != null) {
            backgroundHandler.removeCallbacksAndMessages(null);
        }
        if (backgroundThread != null) {
            backgroundThread.quitSafely();
        }

        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }

        if (speechRecognizer != null) {
            speechRecognizer.destroy();
        }

        if (toneGenerator != null) {
            toneGenerator.release();
        }

        if (requestQueue != null) {
            requestQueue.stop();
        }

        Log.d(TAG, String.format("Session completed: %d documents processed, %d total characters",
                ocrHistory.size(), getTotalCharactersProcessed()));
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopVoiceListening();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (currentState == OCRState.READY_TO_CAPTURE && isTtsReady) {
            startVoiceListening();
        }
    }
}