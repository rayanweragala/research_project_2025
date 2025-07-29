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

public class AddFriendActivity extends AppCompatActivity implements TextToSpeech.OnInitListener, RecognitionListener,IntelligentCaptureManager.CaptureProgressCallback,SmartGlassesConnector.SmartGlassesCallback {

    private static final String TAG = "AddFriendActivity";
    private TextView statusText, instructionsText, nameDisplayText,progressText;
    private Button btnStart,btnStartOver,btnCancel;
    private ImageView captureIndicator,qualityIndicator;
    private ProgressBar captureProgress;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private IntelligentCaptureManager captureManager;
    private SmartGlassesConnector smartGlassesConnector;
    private ToneGenerator toneGenerator;
    private Handler mainHandler;

    private boolean isListening = false;
    private String friendName = "";
    private CaptureState currentState = CaptureState.WAITING_FOR_NAME;

    private static final int TONE_CAPTURE_SUCCESS = ToneGenerator.TONE_PROP_BEEP2;
    private static final int TONE_QUALITY_GOOD = ToneGenerator.TONE_DTMF_1;
    private static final int TONE_COMPLETE = ToneGenerator.TONE_CDMA_CONFIRM;

    private enum CaptureState {
        WAITING_FOR_NAME,
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

        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        captureManager = new IntelligentCaptureManager();
        smartGlassesConnector = new SmartGlassesConnector();
        smartGlassesConnector.setCallback(this);

        mainHandler = new Handler();
        ttsEngine = new TextToSpeech(this, this);

        try {
            toneGenerator = new ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80);
        } catch (RuntimeException e) {
            Log.w(TAG, "Could not create ToneGenerator", e);
        }
    }

    private void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        instructionsText = findViewById(R.id.instructionsText);
        nameDisplayText = findViewById(R.id.nameDisplayText);
        progressText = findViewById(R.id.progressText);
        btnCancel = findViewById(R.id.btnCancel);
        btnStartOver = findViewById(R.id.btnStartOver);
        captureIndicator = findViewById(R.id.captureIndicator);
        qualityIndicator = findViewById(R.id.qualityIndicator);
        captureProgress = findViewById(R.id.captureProgress);

        updateUIForState(CaptureState.WAITING_FOR_NAME);
    }

    private void setupVoiceRecognition() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(this);

        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
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
                statusText.setText("Waiting for name");
                instructionsText.setText("Say the person's name to begin registration");
                captureIndicator.setImageResource(R.drawable.ic_person);
                qualityIndicator.setVisibility(View.GONE);
                captureProgress.setVisibility(View.GONE);
                progressText.setVisibility(View.GONE);
                btnStartOver.setVisibility(View.GONE);
                break;

            case CONNECTING_GLASSES:
                statusText.setText("Connecting to smart glasses");
                instructionsText.setText("Please wait while I connect to your smart glasses...");
                captureIndicator.setImageResource(R.drawable.ic_bluetooth);
                break;

            case READY_TO_CAPTURE:
                statusText.setText("Ready to capture");
                instructionsText.setText("Ask " + friendName + " to face the smart glasses. I'll automatically take photos when ready.");
                captureIndicator.setImageResource(R.drawable.ic_camera_ready);
                qualityIndicator.setVisibility(View.VISIBLE);
                captureProgress.setVisibility(View.VISIBLE);
                progressText.setVisibility(View.VISIBLE);
                captureProgress.setMax(5);
                captureProgress.setProgress(0);
                break;

            case CAPTURING:
                statusText.setText("Capturing face data");
                captureIndicator.setImageResource(R.drawable.ic_camera_on);
                break;

            case PROCESSING:
                statusText.setText("Processing and saving");
                instructionsText.setText("Please wait while I process and save " + friendName + "'s face data...");
                captureIndicator.setImageResource(R.drawable.ic_processing);
                break;

            case COMPLETED:
                statusText.setText("Registration completed!");
                instructionsText.setText(friendName + " has been successfully registered and will be recognized automatically.");
                captureIndicator.setImageResource(R.drawable.ic_check_circle);
                btnStartOver.setVisibility(View.VISIBLE);
                break;

            case ERROR:
                statusText.setText("Error occurred");
                captureIndicator.setImageResource(R.drawable.ic_error);
                btnStartOver.setVisibility(View.VISIBLE);
                break;
        }
    }

    private void startVoiceListening() {
        if (!isListening && speechRecognizer != null) {
            isListening = true;
            speechRecognizer.startListening(speechRecognizerIntent);
        }
    }

    private void stopVoiceListening() {
        if (isListening && speechRecognizer != null) {
            isListening = false;
            speechRecognizer.stopListening();
        }
    }

    private void speak(String text) {
        if (ttsEngine != null) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "utterance_id");
        }
        Log.d(TAG, "TTS: " + text);
    }

    private void playTone(int toneType) {
        if (toneGenerator != null) {
            toneGenerator.startTone(toneType, 200);
        }
    }

    private void resetToInitialState() {
        if (captureManager != null) {
            captureManager.stopCapture();
        }
        if (smartGlassesConnector != null) {
            smartGlassesConnector.stopLiveFeed();
        }

        friendName = "";
        nameDisplayText.setText("Name: Not set");
        updateUIForState(CaptureState.WAITING_FOR_NAME);

        startVoiceListening();
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.getDefault());
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                ttsEngine.setLanguage(Locale.ENGLISH);
            }

            speak("Face registration ready. First, tell me the person's name.");
            startVoiceListening();
        }
    }

    @Override
    public void onResults(Bundle results) {
        isListening = false;
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);

        if (matches != null && !matches.isEmpty()) {
            String spokenText = matches.get(0).trim();
            processSpokenText(spokenText);
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

                    speak("Got it! Name is " + friendName + ". Now connecting to smart glasses.");
                    connectToSmartGlasses();
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
                }
                break;

            default:
                if (currentState == CaptureState.WAITING_FOR_NAME) {
                    startVoiceListening();
                }
                break;
        }
    }
    private void connectToSmartGlasses() {
        updateUIForState(CaptureState.CONNECTING_GLASSES);
        smartGlassesConnector.connect();
    }

    private void startIntelligentCapture() {
        updateUIForState(CaptureState.READY_TO_CAPTURE);

        speak("Ask " + friendName + " to face the smart glasses. I'll automatically take the best photos.");

        captureManager.startIntelligentCapture(friendName, this);

        smartGlassesConnector.startLiveFeed();
    }

    @Override
    public void onCaptureStarted(String personName) {
        updateUIForState(CaptureState.CAPTURING);
        Log.d(TAG, "Capture started for: " + personName);
    }

    @Override
    public void onRealTimeFeedback(String feedback, float qualityScore) {
        int qualityLevel = (int) (qualityScore * 5);

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
        if (qualityScore < 0.3f && Math.random() < 0.1) {
            speak(feedback);
        }
    }

    @Override
    public void onSuccessfulCapture(int captureNumber, String message) {
        playTone(TONE_CAPTURE_SUCCESS);
        speak(message);

        captureProgress.setProgress(captureNumber);

        Log.d(TAG, "Successful capture " + captureNumber + ": " + message);
    }

    @Override
    public void onProgressUpdate(int currentCount, int targetCount, String progressMessage) {
        progressText.setText(currentCount + " / " + targetCount + " photos captured");

        if (Math.random() < 0.3) {
            speak(progressMessage);
        }
    }

    @Override
    public void onCaptureCompleted(String personName, List<IntelligentCaptureManager.CapturedFace> capturedFaces) {
        playTone(TONE_COMPLETE);
        speak("Perfect! I've captured " + capturedFaces.size() + " excellent photos of " + personName + ". Now processing and saving.");

        updateUIForState(CaptureState.PROCESSING);
        smartGlassesConnector.stopLiveFeed();

        processAndSaveCapturedFaces(capturedFaces);
    }

    @Override
    public void onCaptureStopped(String reason) {
        speak("Capture stopped: " + reason);
        updateUIForState(CaptureState.READY_TO_CAPTURE);
    }

    @Override
    public void onError(String error) {
        speak("Error: " + error);
        updateUIForState(CaptureState.ERROR);
        instructionsText.setText("Error: " + error + ". Say 'start over' to try again.");
    }

    private void processAndSaveCapturedFaces(List<IntelligentCaptureManager.CapturedFace> capturedFaces) {
        String[] imageBase64Array = new String[capturedFaces.size()];

        for (int i = 0; i < capturedFaces.size(); i++) {
            Bitmap bitmap = capturedFaces.get(i).bitmap;
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.JPEG, 85, baos);
            byte[] imageBytes = baos.toByteArray();
            imageBase64Array[i] = Base64.encodeToString(imageBytes, Base64.DEFAULT);
        }

        smartGlassesConnector.sendRecognitionData(friendName, imageBase64Array);
    }

    @Override
    public void onConnectionStatusChanged(boolean connected, String message) {
        if (connected) {
            speak("Smart glasses connected successfully!");
            startIntelligentCapture();
        } else {
            speak("Connection failed: " + message);
            updateUIForState(CaptureState.ERROR);
            instructionsText.setText("Smart glasses connection failed. Please check the connection and try again.");
        }
    }

    @Override
    public void onFrameReceived(Bitmap frame, long timestamp, double confidence) {
        if (captureManager != null && captureManager.isCapturing()) {
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

    @Override public void onReadyForSpeech(Bundle params) {}
    @Override public void onBeginningOfSpeech() {}
    @Override public void onRmsChanged(float rmsdB) {}
    @Override public void onBufferReceived(byte[] buffer) {}
    @Override public void onEndOfSpeech() { isListening = false; }
    @Override public void onPartialResults(Bundle partialResults) {}
    @Override public void onEvent(int eventType, Bundle params) {}

    @Override
    public void onError(int error) {
        isListening = false;
        if (error != SpeechRecognizer.ERROR_NO_MATCH && currentState == CaptureState.WAITING_FOR_NAME) {
            mainHandler.postDelayed(this::startVoiceListening, 1000);
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