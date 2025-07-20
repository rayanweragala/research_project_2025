package com.research.blindassistant;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.util.ArrayList;
import java.util.Locale;

public class AddFriendActivity extends AppCompatActivity implements TextToSpeech.OnInitListener, RecognitionListener {

    private TextView statusText, instructionsText, nameDisplayText;
    private Button btnStartCapture, btnSaveFriend, btnCancel, btnRetake;
    private ImageView captureIndicator, previewImage;
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;

    private boolean isCapturing = false;
    private boolean isListening = false;
    private boolean hasCaptured = false;
    private String friendName = "";
    private int captureCount = 0;
    private final int REQUIRED_CAPTURES = 5;
    private Handler mainHandler;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_friend);

        mainHandler = new Handler();
        ttsEngine = new TextToSpeech(this, this);

        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        speak("Face registration ready. First, tell me the person's name, then I'll capture their face from smart glasses.");
    }

    protected void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        instructionsText = findViewById(R.id.instructionsText);
        nameDisplayText = findViewById(R.id.nameDisplayText);
        btnStartCapture = findViewById(R.id.btnStartCapture);
        btnSaveFriend = findViewById(R.id.btnSaveFriend);
        btnCancel = findViewById(R.id.btnCancel);
        btnRetake = findViewById(R.id.btnRetake);
        captureIndicator = findViewById(R.id.captureIndicator);
        previewImage = findViewById(R.id.previewImage);

        updateStatus("Waiting for name");
        updateInstructions("Say the person's name to begin registration");
        btnStartCapture.setEnabled(false);
        btnSaveFriend.setVisibility(View.GONE);
        btnRetake.setVisibility(View.GONE);
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
        btnStartCapture.setOnClickListener(v -> startCapture());

        btnSaveFriend.setOnClickListener(v -> saveFriend());

        btnRetake.setOnClickListener(v -> retakePhotos());

        btnCancel.setOnClickListener(v -> {
            speak("Canceling face registration");
            finish();
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnStartCapture, btnSaveFriend, btnRetake, btnCancel};

        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("Button: " + buttonText);
                return true;
            });
        }
    }

    private void startCapture() {
        if (!isCapturing && !friendName.isEmpty()) {
            isCapturing = true;
            captureCount = 0;

            btnStartCapture.setVisibility(View.GONE);
            btnRetake.setVisibility(View.GONE);
            btnSaveFriend.setVisibility(View.GONE);

            captureIndicator.setImageResource(R.drawable.ic_camera_on);
            updateStatus("Capturing face data...");
            updateInstructions("Hold still. Capturing multiple angles...");

            speak("Starting face capture. Please ask " + friendName + " to look at the smart glasses. I'll take " + REQUIRED_CAPTURES + " photos from different angles.");

            startVoiceListening();
            simulateCapture();
        }
    }

    private void simulateCapture() {
        if (!isCapturing) return;

        mainHandler.postDelayed(() -> {
            if (isCapturing) {
                captureCount++;

                captureIndicator.setImageResource(R.drawable.ic_flash);

                String message = "Captured photo " + captureCount + " of " + REQUIRED_CAPTURES;
                updateStatus(message);
                speak(message);

                previewImage.setImageResource(R.drawable.ic_face_preview);
                previewImage.setVisibility(View.VISIBLE);

                mainHandler.postDelayed(() -> {
                    captureIndicator.setImageResource(R.drawable.ic_camera_on);
                }, 200);

                if (captureCount < REQUIRED_CAPTURES) {
                    simulateCapture();
                } else {
                    completeCaptureProcess();
                }
            }
        }, 2000);
    }

    private void completeCaptureProcess() {
        isCapturing = false;
        hasCaptured = true;

        captureIndicator.setImageResource(R.drawable.ic_check_circle);
        updateStatus("Face capture completed");
        updateInstructions("Say 'SAVE' to register " + friendName + " or 'RETAKE' to capture again");

        btnSaveFriend.setVisibility(View.VISIBLE);
        btnRetake.setVisibility(View.VISIBLE);

        speak("Face capture completed for " + friendName + ". Say save to register them, or retake to capture again.");
    }

    private void saveFriend() {
        if (hasCaptured && !friendName.isEmpty()) {
            updateStatus("Saving friend profile...");
            speak("Saving " + friendName + " to the system. Please wait.");

            mainHandler.postDelayed(() -> {
                updateStatus("Successfully registered!");
                speak(friendName + " has been successfully registered. Returning to main menu.");
                Intent resultIntent = new Intent();
                resultIntent.putExtra("friend_name", friendName);
                resultIntent.putExtra("registration_success", true);
                setResult(RESULT_OK, resultIntent);

                mainHandler.postDelayed(() -> finish(), 2000);
            }, 2000);
        }
    }

    private void retakePhotos() {
        hasCaptured = false;
        captureCount = 0;

        btnSaveFriend.setVisibility(View.GONE);
        btnRetake.setVisibility(View.GONE);
        btnStartCapture.setVisibility(View.VISIBLE);
        btnStartCapture.setEnabled(true);

        previewImage.setVisibility(View.GONE);
        captureIndicator.setImageResource(R.drawable.ic_camera_off);

        updateStatus("Ready to capture");
        updateInstructions("Press capture to start taking photos again");

        speak("Ready to retake photos for " + friendName + ". Press capture when ready.");
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
    }

    private void updateStatus(String status) {
        if (statusText != null) {
            statusText.setText(status);
        }
    }

    private void updateInstructions(String instructions) {
        if (instructionsText != null) {
            instructionsText.setText(instructions);
        }
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.getDefault());
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                ttsEngine.setLanguage(Locale.ENGLISH);
            }
            startVoiceListening();
        }
    }

    @Override
    public void onReadyForSpeech(Bundle params) {
    }

    @Override
    public void onBeginningOfSpeech() {
    }

    @Override
    public void onRmsChanged(float rmsdB) {
    }

    @Override
    public void onBufferReceived(byte[] buffer) {
    }

    @Override
    public void onEndOfSpeech() {
        isListening = false;
    }

    @Override
    public void onError(int error) {
        isListening = false;
        String errorMessage;
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                errorMessage = "Audio recording error";
                break;
            case SpeechRecognizer.ERROR_CLIENT:
                errorMessage = "Client side error";
                break;
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                errorMessage = "Insufficient permissions";
                break;
            case SpeechRecognizer.ERROR_NETWORK:
                errorMessage = "Network error";
                break;
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                errorMessage = "Network timeout";
                break;
            case SpeechRecognizer.ERROR_NO_MATCH:
                errorMessage = "No match found";
                break;
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                errorMessage = "RecognitionService busy";
                break;
            case SpeechRecognizer.ERROR_SERVER:
                errorMessage = "Server error";
                break;
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                errorMessage = "No speech input";
                break;
            default:
                errorMessage = "Unknown error";
                break;
        }

        if (!isCapturing && friendName.isEmpty()) {
            mainHandler.postDelayed(this::startVoiceListening, 1000);
        }
    }

    @Override
    public void onResults(Bundle results) {
        isListening = false;
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);

        if (matches != null && !matches.isEmpty()) {
            String spokenText = matches.get(0).toLowerCase().trim();

            if (friendName.isEmpty()) {
                friendName = capitalizeFirstLetter(spokenText);
                nameDisplayText.setText("Name: " + friendName);
                nameDisplayText.setVisibility(View.VISIBLE);

                updateStatus("Name captured: " + friendName);
                updateInstructions("Press capture to start taking photos");

                btnStartCapture.setEnabled(true);
                btnStartCapture.setVisibility(View.VISIBLE);

                speak("Got it! Name is " + friendName + ". Press capture to start taking photos.");

            } else if (hasCaptured) {
                if (spokenText.contains("save")) {
                    saveFriend();
                } else if (spokenText.contains("retake")) {
                    retakePhotos();
                } else {
                    startVoiceListening();
                }
            } else {
                startVoiceListening();
            }
        } else {
            if (!isCapturing && (friendName.isEmpty() || hasCaptured)) {
                startVoiceListening();
            }
        }
    }

    @Override
    public void onPartialResults(Bundle partialResults) {
    }

    @Override
    public void onEvent(int eventType, Bundle params) {
    }

    private String capitalizeFirstLetter(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }
        return text.substring(0, 1).toUpperCase() + text.substring(1).toLowerCase();
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

        if (mainHandler != null) {
            mainHandler.removeCallbacksAndMessages(null);
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
        if (!isCapturing && friendName.isEmpty()) {
            startVoiceListening();
        }
    }
}