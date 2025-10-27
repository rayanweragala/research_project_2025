package com.research.blindassistant;

import android.content.Intent;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.RecognitionListener;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.ImageView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import java.util.ArrayList;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";

    private Button btnStopSmartGlasses, btnPeopleRecognition, btnTextRecognition;
    private Button btnFieldDescribe, btnNavigation, btnVoiceCommand;
    private Button btnSettings, btnHelp;
    private TextView distanceValueText, distanceZoneText;
    private TextView navigationStatusText, featureStatusText;
    private ImageView voiceIndicator;
    private android.view.View distanceSensorIndicator;

    private DistanceSensorService distanceSensorService;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private TextToSpeech textToSpeech;
    private boolean isListening = false;
    private boolean isTtsReady = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initializeViews();
        initializeServices();
        setupButtonListeners();
    }

    private void initializeViews() {
        distanceValueText = findViewById(R.id.distanceValueText);
        distanceZoneText = findViewById(R.id.distanceZoneText);
        distanceSensorIndicator = findViewById(R.id.distanceSensorIndicator);
        navigationStatusText = findViewById(R.id.navigationStatusText);
        featureStatusText = findViewById(R.id.featureStatusText);
        voiceIndicator = findViewById(R.id.voiceIndicator);

        btnStopSmartGlasses = findViewById(R.id.btnStopSmartGlasses);
        btnPeopleRecognition = findViewById(R.id.btnPeopleRecognition);
        btnTextRecognition = findViewById(R.id.btnTextRecognition);
        btnFieldDescribe = findViewById(R.id.btnFieldDescribe);
        btnNavigation = findViewById(R.id.btnNavigation);
        btnVoiceCommand = findViewById(R.id.btnVoiceCommand);
        btnSettings = findViewById(R.id.btnSettings);
        btnHelp = findViewById(R.id.btnHelp);
    }

    private void initializeServices() {
        initializeTextToSpeech();
        initializeDistanceSensor();
        initializeSpeechRecognition();
    }

    private void initializeTextToSpeech() {
        textToSpeech = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                // Try Sinhala first, fallback to English
                int sinhalaResult = textToSpeech.setLanguage(new Locale("si", "LK"));
                if (sinhalaResult == TextToSpeech.LANG_MISSING_DATA ||
                        sinhalaResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.w(TAG, "Sinhala TTS not available, using English");
                    textToSpeech.setLanguage(Locale.US);
                }

                textToSpeech.setSpeechRate(0.9f);
                textToSpeech.setPitch(1.0f);
                isTtsReady = true;
                Log.d(TAG, "Text-to-Speech initialized");
            } else {
                Log.e(TAG, "Text-to-Speech initialization failed");
            }
        });
    }

    private void speak(String text) {
        if (isTtsReady && textToSpeech != null) {
            textToSpeech.speak(text, TextToSpeech.QUEUE_FLUSH, null, "MainActivity");
        } else {
            Log.w(TAG, "TTS not ready, cannot speak: " + text);
        }
    }

    private void initializeDistanceSensor() {
        distanceSensorService = new DistanceSensorService(this);

        distanceSensorService.setCallback(new DistanceSensorService.DistanceSensorCallback() {
            @Override
            public void onDistanceMeasured(double distance, String zone) {
                runOnUiThread(() -> {
                    distanceValueText.setText(String.format(Locale.US, "Distance: %.1f cm", distance));
                    distanceZoneText.setText("Zone: " + zone);

                    int color = getZoneColor(zone);
                    distanceValueText.setTextColor(color);

                    featureStatusText.setText(String.format(Locale.US,
                            "Distance Sensor Active\nDistance: %.1f cm | Zone: %s\nLast Update: %s",
                            distance, zone, getCurrentTime()));
                });
            }

            @Override
            public void onObstacleDetected(double distance) {
                runOnUiThread(() -> {
                    // Visual feedback
                    distanceValueText.setTextColor(getResources().getColor(android.R.color.holo_red_dark));
                    distanceValueText.setTextSize(28);

                    // TTS Warning in Sinhala - "Stop, obstacle ahead"
                    String warningMessage = "නවතන්න ඉදිරියෙන් බාධකයක්";
                    speak(warningMessage);

                    // Toast notification
                    Toast.makeText(MainActivity.this,
                            String.format(Locale.US, "⚠️ OBSTACLE! %.1f cm", distance),
                            Toast.LENGTH_SHORT).show();

                    // Log the warning
                    Log.w(TAG, String.format("OBSTACLE WARNING: Distance %.1f cm - TTS spoken", distance));

                    // Reset visual feedback after 2 seconds
                    distanceValueText.postDelayed(() -> {
                        distanceValueText.setTextColor(getResources().getColor(R.color.primary_text));
                        distanceValueText.setTextSize(24);
                    }, 2000);
                });
            }

            @Override
            public void onServerStarted(boolean success, String message) {
                runOnUiThread(() -> {
                    navigationStatusText.setText(success ? "Distance Sensor Active" : "Sensor Error");
                    Log.d(TAG, (success ? "Sensor started: " : "Sensor failed: ") + message);
                });
            }

            @Override
            public void onConnectionError(String error) {
                runOnUiThread(() -> {
                    Log.e(TAG, "Distance sensor error: " + error);
                    featureStatusText.setText("Connection Error: " + error);
                });
            }
        });
    }

    private int getZoneColor(String zone) {
        switch (zone.toLowerCase()) {
            case "danger":
                return getResources().getColor(android.R.color.holo_red_dark);
            case "warning":
                return getResources().getColor(android.R.color.holo_orange_dark);
            case "caution":
                return getResources().getColor(android.R.color.holo_orange_light);
            default:
                return getResources().getColor(android.R.color.holo_green_dark);
        }
    }

    private void initializeSpeechRecognition() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            btnVoiceCommand.setEnabled(false);
            return;
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);

        // Create intent for both English and Sinhala
        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);

        // Support multiple languages
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "si-LK");
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "si-LK");

        // Add alternate languages
        ArrayList<String> languages = new ArrayList<>();
        languages.add("si-LK");  // Sinhala
        languages.add("en-US");  // English
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_SUPPORTED_LANGUAGES, languages);

        speechRecognizer.setRecognitionListener(new RecognitionListener() {
            @Override
            public void onReadyForSpeech(Bundle params) {
                isListening = true;
                runOnUiThread(() -> {
                    if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.VISIBLE);
                });
            }

            @Override
            public void onBeginningOfSpeech() {}

            @Override
            public void onRmsChanged(float rmsdB) {}

            @Override
            public void onBufferReceived(byte[] buffer) {}

            @Override
            public void onEndOfSpeech() {
                isListening = false;
                runOnUiThread(() -> {
                    if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);
                });
            }

            @Override
            public void onError(int error) {
                isListening = false;
                runOnUiThread(() -> {
                    if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);
                });
            }

            @Override
            public void onResults(Bundle results) {
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);

                if (matches != null && !matches.isEmpty()) {
                    String spokenText = matches.get(0);
                    runOnUiThread(() -> {
                        if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);
                        handleVoiceCommand(spokenText);
                    });
                }
                isListening = false;
            }

            @Override
            public void onPartialResults(Bundle partialResults) {}

            @Override
            public void onEvent(int eventType, Bundle params) {}
        });
    }

    private void setupButtonListeners() {
        btnStopSmartGlasses.setOnClickListener(v -> {
            speak("නවතමින්");  // "Stopping" in Sinhala
            stopAllServices();
            Toast.makeText(this, "Smart Glasses Stopped", Toast.LENGTH_SHORT).show();
        });

        btnPeopleRecognition.setOnClickListener(v -> {
            speak("මුහුණු හඳුනාගැනීම විවෘත කරමින්");  // "Opening face recognition" in Sinhala
            Intent intent = new Intent(this, EnhancedFaceRecognitionActivity.class);
            startActivity(intent);
        });

        btnTextRecognition.setOnClickListener(v -> {
            speak("පෙළ කියවීම විවෘත කරමින්");  // "Opening text reading" in Sinhala
            Intent intent = new Intent(this, SinhalaOCRActivity.class);
            startActivity(intent);
        });

        btnFieldDescribe.setOnClickListener(v -> {
            speak("දර්ශන විස්තර කිරීම විවෘත කරමින්");  // "Opening scene description" in Sinhala
            Intent intent = new Intent(this, IntelligentCaptureManager.class);
            startActivity(intent);
        });

        btnNavigation.setOnClickListener(v -> {
            speak("නැවිගේෂන් ඉක්මනින් එනවා");  // "Navigation coming soon" in Sinhala
            Toast.makeText(this, "Navigation feature coming soon", Toast.LENGTH_SHORT).show();
        });

        btnVoiceCommand.setOnClickListener(v -> {
            startVoiceRecognition();
        });

        btnSettings.setOnClickListener(v -> {
            speak("සැකසුම් විවෘත කරමින්");  // "Opening settings" in Sinhala
            Intent intent = new Intent(this, SettingsActivity.class);
            startActivity(intent);
        });

        btnHelp.setOnClickListener(v -> {
            speak("උදව් ඉක්මනින් එනවා");  // "Help coming soon" in Sinhala
            Toast.makeText(this, "Help section coming soon", Toast.LENGTH_SHORT).show();
        });
    }

    private void startVoiceRecognition() {
        if (speechRecognizer == null) return;

        if (isListening) {
            speechRecognizer.stopListening();
            isListening = false;
            if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);
            speak("නැවතී");  // "Stopped" in Sinhala
            Toast.makeText(this, "Stopped listening", Toast.LENGTH_SHORT).show();
        } else {
            try {
                speechRecognizer.startListening(speechRecognizerIntent);
                speak("අහනවා");  // "Listening" in Sinhala
                Toast.makeText(this, "🎤 Listening...", Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Log.e(TAG, "Error starting speech recognition", e);
                Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void handleVoiceCommand(String command) {
        command = command.toLowerCase().trim();
        Log.d(TAG, "Voice command received: " + command);
        Toast.makeText(this, "Command: " + command, Toast.LENGTH_SHORT).show();

        // English commands
        if (command.contains("face") || command.contains("people") ||
                command.contains("recognition") || command.contains("person")) {
            btnPeopleRecognition.performClick();
        }
        // Sinhala commands for face recognition: මුහුණ, මුහුණු, හඳුනාගන්න
        else if (command.contains("මුහුණ") || command.contains("මුහුණු") ||
                command.contains("හඳුනාගන්න") || command.contains("පුද්ගල")) {
            btnPeopleRecognition.performClick();
        }
        // English text commands
        else if (command.contains("text") || command.contains("read") ||
                command.contains("ocr") || command.contains("sinhala")) {
            btnTextRecognition.performClick();
        }
        // Sinhala commands for text: පෙළ, කියවන්න, කියවන, ලියන
        else if (command.contains("පෙළ") || command.contains("කියවන") ||
                command.contains("කියවන්න") || command.contains("ලියන")) {
            btnTextRecognition.performClick();
        }
        // English describe commands
        else if (command.contains("describe") || command.contains("scene") ||
                command.contains("field") || command.contains("view") ||
                command.contains("capture")) {
            btnFieldDescribe.performClick();
        }
        // Sinhala commands for describe: විස්තර, දර්ශන, බලන්න
        else if (command.contains("විස්තර") || command.contains("දර්ශන") ||
                command.contains("බලන්න") || command.contains("බලන")) {
            btnFieldDescribe.performClick();
        }
        // English navigation commands
        else if (command.contains("navigate") || command.contains("navigation") ||
                command.contains("direction")) {
            btnNavigation.performClick();
        }
        // Sinhala navigation: මග, දිශාව, යන්න
        else if (command.contains("මග") || command.contains("දිශාව") ||
                command.contains("යන්න")) {
            btnNavigation.performClick();
        }
        // English stop commands
        else if (command.contains("stop") || command.contains("exit") ||
                command.contains("quit")) {
            btnStopSmartGlasses.performClick();
        }
        // Sinhala stop: නවතන්න, නවත, වසන්න
        else if (command.contains("නවතන්න") || command.contains("නවත") ||
                command.contains("වසන්න")) {
            btnStopSmartGlasses.performClick();
        }
        // English settings commands
        else if (command.contains("settings") || command.contains("setting") ||
                command.contains("configuration")) {
            btnSettings.performClick();
        }
        // Sinhala settings: සැකසුම්, සැකසුම
        else if (command.contains("සැකසුම්") || command.contains("සැකසුම")) {
            btnSettings.performClick();
        }
        // English help commands
        else if (command.contains("help") || command.contains("tutorial")) {
            btnHelp.performClick();
        }
        // Sinhala help: උදව්, උදව
        else if (command.contains("උදව්") || command.contains("උදව")) {
            btnHelp.performClick();
        }
        // Distance sensor commands
        else if (command.contains("distance") || command.contains("sensor") ||
                command.contains("දුර") || command.contains("සංවේදකය")) {
            String currentDistance = distanceValueText.getText().toString();
            String currentZone = distanceZoneText.getText().toString();
            speak(currentDistance + ", " + currentZone);
            Toast.makeText(this, currentDistance + ", " + currentZone, Toast.LENGTH_LONG).show();
        }
        // Restart commands
        else if (command.contains("restart") || command.contains("reset") ||
                command.contains("නැවත ආරම්භ") || command.contains("යළි")) {
            if (distanceSensorService != null) {
                distanceSensorService.restart();
                speak("නැවත ආරම්භ කරමින්");  // "Restarting" in Sinhala
                Toast.makeText(this, "Restarting distance sensor", Toast.LENGTH_SHORT).show();
            }
        }
        else {
            speak("විධානය හඳුනාගත නොහැක");  // "Command not recognized" in Sinhala
            Toast.makeText(this, "Command not recognized. Try: 'face', 'text', 'describe'",
                    Toast.LENGTH_LONG).show();
        }
    }

    private String getCurrentTime() {
        return new java.text.SimpleDateFormat("HH:mm:ss", Locale.US).format(new java.util.Date());
    }

    private void stopAllServices() {
        Log.d(TAG, "Stopping all services...");

        if (distanceSensorService != null) {
            distanceSensorService.cleanup();
        }

        if (speechRecognizer != null && isListening) {
            speechRecognizer.stopListening();
            isListening = false;
        }

        if (textToSpeech != null && textToSpeech.isSpeaking()) {
            textToSpeech.stop();
        }

        if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);

        distanceValueText.setText("Distance: -- cm");
        distanceZoneText.setText("Zone: --");
        navigationStatusText.setText("Services Stopped");
        featureStatusText.setText("All services stopped");

        Log.d(TAG, "All services stopped successfully");
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (distanceSensorService != null && !distanceSensorService.isMonitoringActive()) {
            distanceSensorService.restart();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (speechRecognizer != null && isListening) {
            speechRecognizer.stopListening();
            isListening = false;
            if (voiceIndicator != null) voiceIndicator.setVisibility(android.view.View.GONE);
        }

        // Stop TTS when app goes to background
        if (textToSpeech != null && textToSpeech.isSpeaking()) {
            textToSpeech.stop();
        }
    }

    @Override
    protected void onStop() {
        super.onStop();

        // Stop distance sensor monitoring when app is not visible
        if (distanceSensorService != null) {
            distanceSensorService.stopContinuousMonitoring();
            Log.d(TAG, "Distance sensor stopped - app not visible");
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();

        Log.d(TAG, "MainActivity onDestroy - cleaning up all services");

        // Stop and cleanup distance sensor
        if (distanceSensorService != null) {
            distanceSensorService.cleanup();
            distanceSensorService = null;
        }

        // Stop and destroy speech recognizer
        if (speechRecognizer != null) {
            if (isListening) {
                speechRecognizer.stopListening();
            }
            speechRecognizer.destroy();
            speechRecognizer = null;
        }

        // Stop and shutdown text to speech
        if (textToSpeech != null) {
            if (textToSpeech.isSpeaking()) {
                textToSpeech.stop();
            }
            textToSpeech.shutdown();
            textToSpeech = null;
        }

        isTtsReady = false;
        isListening = false;
    }

    @Override
    public void finish() {
        // Ensure cleanup when activity is finishing
        stopAllServices();
        super.finish();
    }

    @Override
    public void onBackPressed() {
        // Show confirmation dialog before exiting
        new androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("Exit Application")
                .setMessage("Are you sure you want to exit? All services will be stopped.")
                .setPositiveButton("Yes, Exit", (dialog, which) -> {
                    stopAllServices();
                    finish();
                    super.onBackPressed();
                })
                .setNegativeButton("Cancel", null)
                .show();
    }
}