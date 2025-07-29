package com.research.blindassistant;

import android.content.Intent;
import android.os.Bundle;
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

public class FaceRecognitionActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener, RecognitionListener {

    private TextView statusText, resultsText, instructionsText;
    private Button btnStartRecognition, btnStopRecognition, btnBack,btnAddFriend;
    private ImageView statusIndicator;
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private boolean isRecognizing = false;
    private boolean isListening = false;

    private boolean iotConnected = true;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_face_recognition);

        ttsEngine = new TextToSpeech(this, this);

        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        speak("Face recognition ready. Smart glasses connected. Say start to begin recognition, or add friend to register new faces.");
    }

    protected void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        resultsText = findViewById(R.id.resultsText);
        instructionsText = findViewById(R.id.instructionsText);
        btnStartRecognition = findViewById(R.id.btnStartRecognition);
        btnStopRecognition = findViewById(R.id.btnStopRecognition);
        btnBack = findViewById(R.id.btnBack);
        statusIndicator = findViewById(R.id.statusIndicator);
        btnAddFriend = findViewById(R.id.btnAddFriend);

        updateConnectionStatus();
        updateInstructions("Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
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
        btnStartRecognition.setOnClickListener(v -> startRecognition());
        btnStopRecognition.setOnClickListener(v -> stopRecognition());
        btnBack.setOnClickListener(v -> {
            speak("Going back to main menu");
            finish();
        });
        btnAddFriend.setOnClickListener(v -> {
            speak("Opening face registration");
            startActivity(new Intent(this, AddFriendActivity.class));
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnStartRecognition, btnStopRecognition, btnBack,btnAddFriend};

        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("Button: " + buttonText);
                return true;
            });
        }
    }

    private void startRecognition() {
        if (!isRecognizing && iotConnected) {
            isRecognizing = true;
            btnStartRecognition.setVisibility(View.GONE);
            btnStopRecognition.setVisibility(View.VISIBLE);
            statusIndicator.setImageResource(R.drawable.ic_visibility_on);

            updateStatus("Recognition Active");
            updateResults("Analyzing smart glasses feed...");
            updateInstructions("Recognition running. Say 'STOP' to end or 'ADD FRIEND' if you see someone new");
            speak("Face recognition started. Analyzing smart glasses feed.");

            startVoiceListening();
            simulateRecognition();
        } else if (!iotConnected) {
            speak("Smart glasses not connected. Please check connection.");
        }
    }

    private void stopRecognition() {
        if (isRecognizing) {
            isRecognizing = false;
            btnStartRecognition.setVisibility(View.VISIBLE);
            btnStopRecognition.setVisibility(View.GONE);
            statusIndicator.setImageResource(R.drawable.ic_visibility_off);

            updateStatus("Recognition Stopped");
            updateResults("Press start to begin recognition");
            updateInstructions("Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
            speak("Face recognition stopped");

            stopVoiceListening();
        }
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

    private void processVoiceCommand(String command) {
        String lowerCommand = command.toLowerCase().trim();

        if (lowerCommand.contains("start") && !isRecognizing) {
            startRecognition();
        } else if (lowerCommand.contains("stop") && isRecognizing) {
            stopRecognition();
        } else if (lowerCommand.contains("add friend") || lowerCommand.contains("add_friend") ||
                lowerCommand.contains("register") || lowerCommand.contains("new face")) {
            speak("Opening face registration");
            startActivity(new Intent(this, AddFriendActivity.class));
        } else if (lowerCommand.contains("back") || lowerCommand.contains("return")) {
            speak("Going back to main menu");
            finish();
        } else if (isRecognizing) {
            speak("Commands available: stop, add friend, or back");
        } else {
            speak("Commands available: start, add friend, or back");
        }
    }

    private void simulateRecognition() {
        if (!isRecognizing) return;

        new android.os.Handler().postDelayed(() -> {
            if (isRecognizing) {
                String[] possibleResults = {
                        "John detected 2 meters ahead",
                        "Sarah identified on your left",
                        "Unknown person detected 3 meters away",
                        "Mike found at 1 o'clock direction",
                        "No faces currently visible"
                };

                String result = possibleResults[(int)(Math.random() * possibleResults.length)];
                updateResults(result);
                speak(result);

                simulateRecognition();
            }
        }, 3000 + (int)(Math.random() * 2000));
    }

    private void updateStatus(String message) {
        statusText.setText(message);
        statusText.setContentDescription(message);
    }

    private void updateResults(String results) {
        resultsText.setText(results);
        resultsText.setContentDescription("Recognition result: " + results);
    }

    private void updateInstructions(String instructions) {
        instructionsText.setText(instructions);
        instructionsText.setContentDescription("Instructions: " + instructions);
    }

    private void updateConnectionStatus() {
        if (iotConnected) {
            statusIndicator.setImageResource(R.drawable.ic_bluetooth_connected);
            statusIndicator.setContentDescription("Smart glasses connected");
        } else {
            statusIndicator.setImageResource(R.drawable.ic_bluetooth_disabled);
            statusIndicator.setContentDescription("Smart glasses disconnected");
        }
    }

    private void speak(String text) {
        if (ttsEngine != null) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "BLIND_ASSISTANT_UTTERANCE");
        }
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches != null && !matches.isEmpty()) {
            String recognizedText = matches.get(0);
            processVoiceCommand(recognizedText);
        }

        if (isListening && isRecognizing) {
            new android.os.Handler().postDelayed(() -> {
                if (isListening && isRecognizing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override
    public void onError(int error) {
        if (error != SpeechRecognizer.ERROR_NO_MATCH && isListening) {
            new android.os.Handler().postDelayed(() -> {
                if (isListening && isRecognizing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override
    public void onReadyForSpeech(Bundle params) {}
    @Override
    public void onBeginningOfSpeech() {}
    @Override
    public void onRmsChanged(float rmsdB) {}
    @Override
    public void onBufferReceived(byte[] buffer) {}
    @Override
    public void onEndOfSpeech() {}
    @Override
    public void onPartialResults(Bundle partialResults) {}
    @Override
    public void onEvent(int eventType, Bundle params) {}

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.US);
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                updateStatus("TTS Language not supported");
            } else {
                new android.os.Handler().postDelayed(() -> {
                    startVoiceListening();
                }, 1000);
            }
        }
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
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopVoiceListening();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (isRecognizing) {
            startVoiceListening();
        }
    }
}