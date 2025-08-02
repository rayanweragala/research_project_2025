package com.research.blindassistant;

import android.content.Intent;
import android.graphics.Bitmap;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.Bundle;
import android.os.Handler;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Base64;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class AddFriendActivity extends AppCompatActivity implements TextToSpeech.OnInitListener, RecognitionListener,IntelligentCaptureManager.CaptureProgressCallback,SmartGlassesConnector.SmartGlassesCallback,FaceRecognitionService.FaceRecognitionCallback {

    private static final String TAG = "AddFriendActivity";
    private TextView statusText, instructionsText, nameDisplayText,progressText;
    private Button btnStart,btnStartOver,btnCancel;
    private ImageView captureIndicator,qualityIndicator;
    private ProgressBar captureProgress;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private IntelligentCaptureManager captureManager;
    private MockSmartGlassesConnector smartGlassesConnector;

    private FaceRecognitionService faceRecognitionService;
    private ToneGenerator toneGenerator;
    private Handler mainHandler;

    private boolean isListening = false;
    private boolean isTtsReady = false;
    private String friendName = "";
    private CaptureState currentState = CaptureState.WAITING_FOR_NAME;
    private int speechRetryCount = 0;
    private static final int MAX_SPEECH_RETRIES = 3;

    private static final int TONE_CAPTURE_SUCCESS = ToneGenerator.TONE_PROP_BEEP2;
    private static final int TONE_QUALITY_GOOD = ToneGenerator.TONE_DTMF_1;
    private static final int TONE_COMPLETE = ToneGenerator.TONE_CDMA_CONFIRM;
    private static final int TONE_ERROR = ToneGenerator.TONE_CDMA_ABBR_ALERT;

    private StatusManager statusManager;

    private enum CaptureState {
        WAITING_FOR_NAME,
        CHECKING_SERVER,
        CONNECTING_GLASSES,
        READY_TO_CAPTURE,
        CAPTURING,
        PROCESSING,
        COMPLETED,
        ERROR
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_friend_enhanced);
        setupServices();
        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        mainHandler = new Handler();
        ttsEngine = new TextToSpeech(this, this);

        try {
            toneGenerator = new ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80);
        } catch (RuntimeException e) {
            Log.w(TAG, "Could not create ToneGenerator", e);
        }
    }

    private void setupServices(){
        statusManager = new StatusManager(this);
        faceRecognitionService = new FaceRecognitionService(this);
        faceRecognitionService.setCallback(this);

        captureManager = new IntelligentCaptureManager();

        smartGlassesConnector = new MockSmartGlassesConnector(this);
        smartGlassesConnector.setCallback(this);
        smartGlassesConnector.setFaceRecognitionService(faceRecognitionService);
    }

    private void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        instructionsText = findViewById(R.id.instructionsText);
        nameDisplayText = findViewById(R.id.nameDisplayText);
        progressText = findViewById(R.id.progressText);
        btnCancel = findViewById(R.id.btnCancel);
        btnStartOver = findViewById(R.id.btnStartOver);
        captureIndicator = findViewById(R.id.statusIndicator);
        qualityIndicator = findViewById(R.id.qualityIndicator);
        captureProgress = findViewById(R.id.captureProgress);

        updateUIForState(CaptureState.WAITING_FOR_NAME);
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
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, getPackageName());
    }

    private void setupButtons() {
        btnCancel.setOnClickListener(v -> {
            speak("Canceling face registration");
            finishActivity();
        });

        btnStartOver.setOnClickListener(v -> {
            speak("Starting over");
            resetToInitialState();
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnCancel, btnStartOver};
        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("Button: " + buttonText);
                return true;
            });
        }
    }

    private void updateUIForState(CaptureState newState) {
        currentState = newState;

        switch (newState) {
            case WAITING_FOR_NAME:
                statusManager.updateStatus(StatusManager.ConnectionStatus.WAITING_INPUT,
                        "Waiting for name", "Say the person's name to begin");
                instructionsText.setText("Say the person's name to begin registration");
                qualityIndicator.setVisibility(View.GONE);
                captureProgress.setVisibility(View.GONE);
                progressText.setVisibility(View.GONE);
                btnStartOver.setVisibility(View.GONE);
                break;

            case CHECKING_SERVER:
                statusManager.updateStatus(StatusManager.ConnectionStatus.CHECKING_SERVER,
                        "Checking face recognition server", "Verifying face recognition system...");
                instructionsText.setText("Please wait while I check the face recognition system...");
                break;

            case CONNECTING_GLASSES:
                statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTING,
                        "Connecting to smart glasses", "Establishing smart glasses connection...");
                instructionsText.setText("Please wait while I connect to your smart glasses...");
                break;

            case READY_TO_CAPTURE:
                statusManager.updateStatus(StatusManager.ConnectionStatus.READY_TO_CAPTURE,
                        "Ready to capture", "Ask " + friendName + " to face the smart glasses");
                instructionsText.setText("Ask " + friendName + " to face the smart glasses. I'll automatically take photos when ready.");
                qualityIndicator.setVisibility(View.VISIBLE);
                captureProgress.setVisibility(View.VISIBLE);
                progressText.setVisibility(View.VISIBLE);
                captureProgress.setMax(5);
                captureProgress.setProgress(0);
                break;

            case CAPTURING:
                statusManager.updateStatus(StatusManager.ConnectionStatus.CAPTURING,
                        "Capturing face data", "Taking photos automatically...");
                instructionsText.setText("Stay still while I capture the best photos...");
                break;

            case PROCESSING:
                statusManager.updateStatus(StatusManager.ConnectionStatus.PROCESSING,
                        "Processing with AI model", "Saving " + friendName + "'s face data...");
                instructionsText.setText("Please wait while the InsightFace AI processes and saves " + friendName + "'s face data...");
                break;

            case COMPLETED:
                statusManager.updateStatus(StatusManager.ConnectionStatus.SUCCESS,
                        "Registration completed!", friendName + " successfully registered");
                instructionsText.setText(friendName + " has been successfully registered and will be recognized automatically.");
                btnStartOver.setVisibility(View.VISIBLE);
                break;

            case ERROR:
                statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                        "Error occurred", "Registration failed");
                instructionsText.setText("An error occurred. Press 'Start Over' to try again.");
                btnStartOver.setVisibility(View.VISIBLE);
                break;
        }
    }

    private void startVoiceListening() {
        if (!isTtsReady) {
            Log.w(TAG, "TTS not ready, delaying voice listening");
            mainHandler.postDelayed(this::startVoiceListening, 1000);
            return;
        }

        if (speechRecognizer == null) {
            Log.e(TAG, "Speech recognizer is null, cannot start listening");
            return;
        }

        if (!isListening) {
            Log.d(TAG, "Starting voice listening, retry count: " + speechRetryCount);
            isListening = true;
            try {
                speechRecognizer.startListening(speechRecognizerIntent);
            } catch (Exception e) {
                Log.e(TAG, "Error starting speech recognition", e);
                isListening = false;
                handleSpeechRecognitionError();
            }
        }
    }

    private void stopVoiceListening() {
        if (isListening && speechRecognizer != null) {
            Log.d(TAG, "Stopping voice listening");
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
            Log.w(TAG, "TTS not ready, queuing message: " + text);
            mainHandler.postDelayed(() -> {
                if (ttsEngine != null && isTtsReady) {
                    ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "utterance_id");
                }
            }, 500);
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

    private void resetToInitialState() {
        Log.d(TAG, "Resetting to initial state");

        stopVoiceListening();

        if (captureManager != null) {
            captureManager.stopCapture();
        }
        if (smartGlassesConnector != null) {
            smartGlassesConnector.stopLiveFeed();
        }

        friendName = "";
        speechRetryCount = 0;
        nameDisplayText.setText("Name: Not set");
        updateUIForState(CaptureState.WAITING_FOR_NAME);

        mainHandler.postDelayed(this::startVoiceListening, 1000);
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.getDefault());
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                ttsEngine.setLanguage(Locale.ENGLISH);
            }

            isTtsReady = true;
            Log.d(TAG, "TTS initialized successfully");

            speak("Face registration ready. First, tell me the person's name.");

            mainHandler.postDelayed(this::startVoiceListening, 2000);
        } else {
            Log.e(TAG, "TTS initialization failed");
            isTtsReady = false;
        }
    }

    @Override
    public void onResults(Bundle results) {
        Log.d(TAG, "Speech recognition results received");
        isListening = false;
        speechRetryCount = 0;

        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);

        if (matches != null && !matches.isEmpty()) {
            String spokenText = matches.get(0).trim();
            Log.d(TAG, "Recognized speech: " + spokenText);
            processSpokenText(spokenText);
        } else {
            Log.w(TAG, "No speech matches found");
            handleSpeechRecognitionError();
        }
    }

    private void processSpokenText(String spokenText) {
        Log.d(TAG, "Processing spoken text: " + spokenText);

        switch (currentState) {
            case WAITING_FOR_NAME:
                if (!spokenText.toLowerCase().contains("cancel")) {
                    friendName = capitalizeFirstLetter(spokenText);
                    nameDisplayText.setText("Name: " + friendName);
                    nameDisplayText.setVisibility(View.VISIBLE);

                    speak("Got it! Name is " + friendName + ". Now checking face recognition server.");
                    checkFaceRecognitionServer();
                } else {
                    speak("Canceling registration");
                    finishActivity();
                }
                break;

            case READY_TO_CAPTURE:
            case CAPTURING:
                String lowerText = spokenText.toLowerCase();
                if (lowerText.contains("stop") || lowerText.contains("cancel")) {
                    captureManager.stopCapture();
                    speak("Stopping capture");
                } else if (lowerText.contains("start over")) {
                    resetToInitialState();
                } else {
                    startVoiceListening();
                }
                break;

            default:
                Log.d(TAG, "Speech not processed in current state: " + currentState);
                break;
        }
    }

    private void handleSpeechRecognitionError() {
        if (speechRetryCount < MAX_SPEECH_RETRIES) {
            speechRetryCount++;
            Log.d(TAG, "Retrying speech recognition, attempt: " + speechRetryCount);

            if (currentState == CaptureState.WAITING_FOR_NAME) {
                speak("I didn't catch that. Please say the person's name again.");
                mainHandler.postDelayed(this::startVoiceListening, 2000);
            }
        } else {
            Log.e(TAG, "Max speech recognition retries reached");
            speak("I'm having trouble hearing you. Please use the start over button to try again.");
            updateUIForState(CaptureState.ERROR);
            instructionsText.setText("Speech recognition failed. Please press 'Start Over' to try again.");
        }
    }

    private void checkFaceRecognitionServer() {
        updateUIForState(CaptureState.CHECKING_SERVER);
        if (faceRecognitionService != null) {
            faceRecognitionService.checkServerHealth();
        } else {
            Log.e(TAG, "Face recognition service is null");
            onConnectionError("Face recognition service not available");
        }
    }

    private void connectToSmartGlasses() {
        updateUIForState(CaptureState.CONNECTING_GLASSES);
        if (smartGlassesConnector != null) {
            smartGlassesConnector.connect();
        } else {
            Log.e(TAG, "Smart glasses connector is null");
            onConnectionStatusChanged(false, "Smart glasses connector not available");
        }
    }

    private void startIntelligentCapture() {
        updateUIForState(CaptureState.READY_TO_CAPTURE);

        speak("Ask " + friendName + " to face the smart glasses. I'll automatically take the best photos.");

        if (captureManager != null && smartGlassesConnector != null) {
            captureManager.startIntelligentCapture(friendName, this);
            smartGlassesConnector.startLiveFeed();

            mainHandler.postDelayed(this::startVoiceListening, 3000);
        } else {
            Log.e(TAG, "Capture manager or smart glasses connector is null");
            onError("System components not available");
        }
    }


    @Override
    public void onCaptureStarted(String personName) {
        updateUIForState(CaptureState.CAPTURING);
        Log.d(TAG, "Capture started for: " + personName);
    }

    @Override
    public void onRealTimeFeedback(String feedback, float qualityScore) {
        Log.d(TAG, String.format("Real-time feedback: score=%.2f, feedback='%s'", qualityScore, feedback));
        int qualityLevel = (int) (qualityScore * 5);

        runOnUiThread(() -> {
            switch (qualityLevel) {
                case 0:
                case 1:
                    qualityIndicator.setImageResource(R.drawable.ic_quality_poor);
                    break;
                case 2:
                case 3:
                    qualityIndicator.setImageResource(R.drawable.ic_quality_medium);
                    break;
                case 4:
                case 5:
                    qualityIndicator.setImageResource(R.drawable.ic_quality_good);
                    if (qualityScore > 0.8f) {
                        playTone(TONE_QUALITY_GOOD);
                    }
                    break;
            }
        });

        if (qualityScore < 0.5f && Math.random() < 0.3) {
            speak(feedback);
        }
    }

    @Override
    public void onSuccessfulCapture(int captureNumber, String message) {
        Log.d(TAG, "Successful capture #" + captureNumber + ": " + message);
        playTone(TONE_CAPTURE_SUCCESS);
        speak(message);

        runOnUiThread(() -> {
            captureProgress.setProgress(captureNumber);
            progressText.setText(captureNumber + " photos captured");
        });
    }

    @Override
    public void onProgressUpdate(int currentCount, int targetCount, String progressMessage) {
        runOnUiThread(() -> {
            progressText.setText(currentCount + " / " + targetCount + " photos captured");
        });

        if (Math.random() < 0.5) {
            speak(progressMessage);
        }
    }

    @Override
    public void onCaptureCompleted(String personName, List<IntelligentCaptureManager.CapturedFace> capturedFaces) {
        playTone(TONE_COMPLETE);
        speak("Perfect! I've captured " + capturedFaces.size() + " excellent photos of " + personName + ". Now processing and saving.");

        updateUIForState(CaptureState.PROCESSING);
        stopVoiceListening();

        if (smartGlassesConnector != null) {
            smartGlassesConnector.stopLiveFeed();
        }

        for (int i = 0; i < capturedFaces.size(); i++) {
            IntelligentCaptureManager.CapturedFace face = capturedFaces.get(i);
            Log.d(TAG, String.format("Captured face %d: %dx%d, quality=%.2f, angle=%s",
                    i+1, face.bitmap.getWidth(), face.bitmap.getHeight(), face.qualityScore, face.faceAngle));
        }
        processAndSaveCapturedFaces(capturedFaces);
    }

    @Override
    public void onCaptureStopped(String reason) {
        speak("Capture stopped: " + reason);
        updateUIForState(CaptureState.READY_TO_CAPTURE);
        mainHandler.postDelayed(this::startVoiceListening, 2000);
    }

    @Override
    public void onError(String error) {
        Log.e(TAG, "Capture error: " + error);
        playTone(TONE_ERROR);
        speak("Error: " + error);
        updateUIForState(CaptureState.ERROR);
        instructionsText.setText("Error: " + error + ". Press 'Start Over' to try again.");
        stopVoiceListening();
    }

    private void processAndSaveCapturedFaces(List<IntelligentCaptureManager.CapturedFace> capturedFaces) {
        Log.d(TAG, "Processing " + capturedFaces.size() + " captured faces for saving");

        try {
            String[] imageBase64Array = new String[capturedFaces.size()];

            for (int i = 0; i < capturedFaces.size(); i++) {
                Bitmap bitmap = capturedFaces.get(i).bitmap;
                Log.d(TAG, "Processing face " + (i+1) + ": " + bitmap.getWidth() + "x" + bitmap.getHeight());

                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                bitmap.compress(Bitmap.CompressFormat.JPEG, 85, baos);
                byte[] imageBytes = baos.toByteArray();
                Log.d(TAG, "Compressed face " + (i+1) + " to " + imageBytes.length + " bytes");
                imageBase64Array[i] = Base64.encodeToString(imageBytes, Base64.DEFAULT);
                Log.d(TAG, "Base64 encoded face " + (i+1) + " length: " + imageBase64Array[i].length());
            }

            Log.d(TAG, "Sending " + imageBase64Array.length + " images to smart glasses connector");
            if (smartGlassesConnector != null) {
                smartGlassesConnector.sendRecognitionData(friendName, imageBase64Array);
            } else {
                Log.e(TAG, "Smart glasses connector is null");
                onError("Smart glasses connection lost");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error processing captured faces", e);
            onError("Failed to process captured images");
        }
    }

    @Override
    public void onConnectionStatusChanged(boolean connected, String message) {
        if (connected) {
            speak("Smart glasses connected successfully!");
            startIntelligentCapture();
        } else {
            playTone(TONE_ERROR);
            speak("Connection failed: " + message);
            updateUIForState(CaptureState.ERROR);
            instructionsText.setText("Smart glasses connection failed. Please check the connection and try again.");
        }
    }

    @Override
    public void onFrameReceived(Bitmap frame, long timestamp, double confidence) {
        Log.d(TAG, "Frame received in AddFriendActivity: " + frame.getWidth() + "x" + frame.getHeight());

        if (captureManager != null && captureManager.isCapturing()) {
            Log.d(TAG, "Forwarding frame to capture manager - currently captured: " + captureManager.getCaptureCount());
            captureManager.processCandidateFrame(frame);
        }
    }

    @Override
    public void onFeedStopped() {
        Log.d(TAG, "Smart glasses feed stopped");
    }

    @Override
    public void onPersonRegistered(String personName) {
        speak("Excellent! " + personName + " has been successfully registered in the smart glasses system. They will now be recognized automatically.");

        updateUIForState(CaptureState.COMPLETED);

        mainHandler.postDelayed(() -> {
            Intent resultIntent = new Intent();
            resultIntent.putExtra("friend_name", friendName);
            resultIntent.putExtra("registration_success", true);
            setResult(RESULT_OK, resultIntent);
            finish();
        }, 3000);
    }

    @Override
    public void onPersonRecognized(String name, float confidence, String message){
        Log.d(TAG, "Person recognized: " + name + " (" + confidence + ")");
    }

    @Override
    public void onPersonRegistered(String name, boolean success, String message) {
        if (success) {
            speak("Face registration successful! " + message);
            onPersonRegistered(name);
        } else {
            playTone(TONE_ERROR);
            speak("Registration failed: " + message);
            updateUIForState(CaptureState.ERROR);
            instructionsText.setText("Registration failed: " + message + ". Press 'Start Over' to try again.");
        }
    }

    @Override
    public void onConnectionError(String error) {
        playTone(TONE_ERROR);
        speak("Face recognition server error: " + error);
        updateUIForState(CaptureState.ERROR);
        instructionsText.setText("Server connection error: " + error + ". Please check your network and server status.");
    }

    @Override
    public void onServerHealthCheck(boolean healthy, int peopleCount) {
        if (healthy) {
            speak("Face recognition server is ready. " + peopleCount + " people currently registered. Now connecting to smart glasses.");
            connectToSmartGlasses();
        } else {
            playTone(TONE_ERROR);
            speak("Face recognition server is not responding");
            updateUIForState(CaptureState.ERROR);
            instructionsText.setText("Face recognition server is not available. Please start the server and try again.");
        }
    }

    @Override
    public void onReadyForSpeech(Bundle params) {
        Log.d(TAG, "Speech recognizer ready");
    }

    @Override
    public void onBeginningOfSpeech() {
        Log.d(TAG, "User started speaking");
    }

    @Override
    public void onRmsChanged(float rmsdB) {
    }

    @Override
    public void onBufferReceived(byte[] buffer) {
    }

    @Override
    public void onEndOfSpeech() {
        Log.d(TAG, "User stopped speaking");
        isListening = false;
    }

    @Override
    public void onPartialResults(Bundle partialResults) {
    }

    @Override
    public void onEvent(int eventType, Bundle params) {
        Log.d(TAG, "Speech recognition event: " + eventType);
    }

    @Override
    public void onError(int error) {
        isListening = false;
        String errorMessage = getSpeechErrorMessage(error);
        Log.e(TAG, "Speech recognition error: " + error + " - " + errorMessage);

        switch (error) {
            case SpeechRecognizer.ERROR_NO_MATCH:
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                handleSpeechRecognitionError();
                break;

            case SpeechRecognizer.ERROR_AUDIO:
            case SpeechRecognizer.ERROR_CLIENT:
                Log.e(TAG, "Critical speech recognition error: " + errorMessage);
                speak("Speech recognition unavailable. Please use the buttons to navigate.");
                break;

            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                speak("Network error. Please check your connection and try again.");
                handleSpeechRecognitionError();
                break;

            default:
                handleSpeechRecognitionError();
                break;
        }
    }

    private String getSpeechErrorMessage(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO: return "Audio recording error";
            case SpeechRecognizer.ERROR_CLIENT: return "Client side error";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "Insufficient permissions";
            case SpeechRecognizer.ERROR_NETWORK: return "Network error";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "Network timeout";
            case SpeechRecognizer.ERROR_NO_MATCH: return "No speech match";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "Recognition service busy";
            case SpeechRecognizer.ERROR_SERVER: return "Server error";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "No speech input";
            default: return "Unknown error";
        }
    }

    private String capitalizeFirstLetter(String text) {
        if (text == null || text.isEmpty()) return text;
        return text.substring(0, 1).toUpperCase() + text.substring(1).toLowerCase();
    }

    private void finishActivity() {
        setResult(RESULT_CANCELED);
        finish();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "Destroying activity");

        stopVoiceListening();

        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }

        if (speechRecognizer != null) {
            speechRecognizer.destroy();
        }

        if (captureManager != null) {
            captureManager.cleanup();
        }

        if (smartGlassesConnector != null) {
            smartGlassesConnector.cleanup();
        }

        if(faceRecognitionService != null){
            faceRecognitionService.cleanup();
        }

        if (toneGenerator != null) {
            toneGenerator.release();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopVoiceListening();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (currentState == CaptureState.WAITING_FOR_NAME) {
            startVoiceListening();
        }
    }
}