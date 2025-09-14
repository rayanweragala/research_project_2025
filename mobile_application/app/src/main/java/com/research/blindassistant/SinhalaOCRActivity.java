package com.research.blindassistant;

import android.graphics.Bitmap;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.util.Locale;

public class SinhalaOCRActivity extends AppCompatActivity implements OCRService.OCRCallback {

    private static final String TAG = "SinhalaOCRActivity";

    private CameraManager cameraManager;
    private OCRService ocrService;
    private TextToSpeech textToSpeech;

    private ImageView cameraFeedView;
    private ProgressBar processingIndicator;
    private TextView statusText, documentTypeText, extractedText;
    private TextView confidenceText, processingTimeText, qualityScoreText;
    private ImageButton speakButton, copyButton;
    private Button startRecognitionButton, stopRecognitionButton;
    private View noFeedMessage;

    private boolean isProcessing = false;
    private String currentExtractedText = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_sinhala_ocr);

        initializeViews();
        setupServices();
        setupButtons();
    }

    private void initializeViews() {
        cameraFeedView = findViewById(R.id.cameraFeedView);
        processingIndicator = findViewById(R.id.processingIndicator);
        statusText = findViewById(R.id.statusText);
        documentTypeText = findViewById(R.id.documentTypeText);
        extractedText = findViewById(R.id.extractedText);
        confidenceText = findViewById(R.id.confidenceText);
        processingTimeText = findViewById(R.id.processingTimeText);
        qualityScoreText = findViewById(R.id.qualityScoreText);
        speakButton = findViewById(R.id.speakButton);
        copyButton = findViewById(R.id.copyButton);
        startRecognitionButton = findViewById(R.id.startRecognitionButton);
        stopRecognitionButton = findViewById(R.id.stopRecognitionButton);
        noFeedMessage = findViewById(R.id.noFeedMessage);
    }

    private void setupServices() {
        // Initialize camera manager (reuse your existing camera implementation)
        cameraManager = new CameraManager(this, cameraFeedView);

        // Initialize OCR service
        ocrService = new OCRService(this);
        ocrService.setCallback(this);

        // Initialize Text-to-Speech
        textToSpeech = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                int result = textToSpeech.setLanguage(Locale.ENGLISH);
                // You might want to add Sinhala language support if available
                if (result == TextToSpeech.LANG_MISSING_DATA ||
                        result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.e(TAG, "TTS Language not supported");
                }
            } else {
                Log.e(TAG, "TTS Initialization failed");
            }
        });
    }

    private void setupButtons() {
        startRecognitionButton.setOnClickListener(v -> startOCRProcess());
        stopRecognitionButton.setOnClickListener(v -> stopOCRProcess());

        speakButton.setOnClickListener(v -> speakExtractedText());
        copyButton.setOnClickListener(v -> copyExtractedText());
    }

    private void startOCRProcess() {
        if (isProcessing) return;

        isProcessing = true;
        startRecognitionButton.setEnabled(false);
        stopRecognitionButton.setEnabled(true);
        processingIndicator.setVisibility(View.VISIBLE);
        statusText.setText("Processing document...");

        // Capture current frame
        Bitmap currentFrame = cameraManager.captureFrame();
        if (currentFrame != null) {
            ocrService.processDocument(currentFrame);
        } else {
            statusText.setText("Failed to capture frame");
            resetUIState();
        }
    }

    private void stopOCRProcess() {
        isProcessing = false;
        resetUIState();
    }

    private void resetUIState() {
        startRecognitionButton.setEnabled(true);
        stopRecognitionButton.setEnabled(false);
        processingIndicator.setVisibility(View.GONE);
    }

    private void speakExtractedText() {
        if (currentExtractedText.isEmpty()) return;

        // Use server-side TTS or local TTS
        // ocrService.speakText(currentExtractedText); // Server-side

        // Local TTS
        textToSpeech.speak(currentExtractedText, TextToSpeech.QUEUE_FLUSH, null, "ocr_tts");
    }

    private void copyExtractedText() {
        if (currentExtractedText.isEmpty()) return;

        android.content.ClipboardManager clipboard =
                (android.content.ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        android.content.ClipData clip =
                android.content.ClipData.newPlainText("Extracted Text", currentExtractedText);
        clipboard.setPrimaryClip(clip);

        // Show toast or other feedback
        statusText.setText("Text copied to clipboard");
    }

    // OCRService Callbacks
    @Override
    public void onOCRResult(String documentType, float confidence, String extractedText,
                            float qualityScore, long processingTime) {
        runOnUiThread(() -> {
            isProcessing = false;
            resetUIState();

            documentTypeText.setText(documentType);
            this.extractedText.setText(extractedText);
            currentExtractedText = extractedText;

            confidenceText.setText(String.format("Confidence: %.1f%%", confidence * 100));
            processingTimeText.setText(String.format("Time: %dms", processingTime));
            qualityScoreText.setText(String.format("Quality: %.1f%%", qualityScore * 100));

            // Enable action buttons
            speakButton.setEnabled(true);
            copyButton.setEnabled(true);

            statusText.setText("OCR completed successfully");
        });
    }

    @Override
    public void onOCRError(String error) {
        runOnUiThread(() -> {
            isProcessing = false;
            resetUIState();
            statusText.setText("OCR Error: " + error);
        });
    }

    @Override
    public void onTTSResult(boolean success, String message) {
        runOnUiThread(() -> {
            statusText.setText("TTS: " + message);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        cameraManager.startCamera();
    }

    @Override
    protected void onPause() {
        super.onPause();
        cameraManager.stopCamera();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ocrService != null) {
            ocrService.cleanup();
        }
        if (textToSpeech != null) {
            textToSpeech.stop();
            textToSpeech.shutdown();
        }
        if (cameraManager != null) {
            cameraManager.cleanup();
        }
    }
}