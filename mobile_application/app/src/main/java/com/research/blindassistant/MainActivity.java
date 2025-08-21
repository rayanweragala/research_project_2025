package com.research.blindassistant;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.app.NotificationManagerCompat;

import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.Locale;

import static com.research.blindassistant.StringResources.Main;

public class MainActivity extends AppCompatActivity implements TextToSpeech.OnInitListener,RecognitionListener {

    private Button btnPeopleRecognition,btnVoiceCommand,btnNavigation,btnSettings, btnStopSmartGlasses;
    private TextView statusText;
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private boolean isListening = false;
    private static final int PERMISSION_REQUEST_RECORD_AUDIO = 1;
    private static final int PERMISSION_REQUEST_NOTIFICATIONS = 2;

    private void loadSavedLanguagePreference() {
        String langCode = getSharedPreferences("blind_assistant_prefs",MODE_PRIVATE)
                .getString("selected_language", "en");
        Locale savedLocale = langCode.equals("si") ? StringResources.LOCALE_SINHALA : StringResources.LOCALE_ENGLISH;
        StringResources.setLocale(savedLocale);
    }

    private void updateSpeechRecognitionLanguage() {
        Locale currentLocale = StringResources.getCurrentLocale();
        speechRecognizerIntent.removeExtra(RecognizerIntent.EXTRA_LANGUAGE);
        if (currentLocale.equals(StringResources.LOCALE_SINHALA)) {
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "si-LK");
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_CONFIDENCE_SCORES, true);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "si-LK");
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
        } else {
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US");
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        loadSavedLanguagePreference();

        ttsEngine = new TextToSpeech(this, this);
        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        speak(StringResources.getString(Main.ASSISTANT_READY), StringResources.getCurrentLocale());

        ensureForegroundMonitoring();
    }
    private void initializeComponents() {
        btnPeopleRecognition = findViewById(R.id.btnPeopleRecognition);
        btnVoiceCommand = findViewById(R.id.btnVoiceCommand);
        btnNavigation = findViewById(R.id.btnNavigation);
        btnSettings = findViewById(R.id.btnSettings);
        statusText = findViewById(R.id.statusText);
        btnStopSmartGlasses = findViewById(R.id.btnStopSmartGlasses);
    }

    private void setupVoiceRecognition() {

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO}, PERMISSION_REQUEST_RECORD_AUDIO);
        }

        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Log.e("MainActivity", "Speech recognition is not available on this device");
            updateStatus("Speech recognition not available on this device");
            speak("Speech recognition is not available on this device", StringResources.getCurrentLocale());
            return;
        }

        try {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            speechRecognizer.setRecognitionListener(this);

            speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);

            updateSpeechRecognitionLanguage();
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        } catch (Exception e) {
            Log.e("MainActivity", "Error initializing speech recognizer: " + e.getMessage());
            updateStatus("Error initializing speech recognition");
            speak("Error initializing speech recognition", StringResources.getCurrentLocale());
        }
    }

    private void ensureForegroundMonitoring() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{android.Manifest.permission.POST_NOTIFICATIONS},
                        PERMISSION_REQUEST_NOTIFICATIONS);
            }
        }

        try {
            getSharedPreferences("blind_assistant_prefs", MODE_PRIVATE)
                    .edit().putBoolean("monitoring_enabled", true).apply();

            Intent svc = new Intent(this, SmartGlassesForegroundService.class);
            svc.setAction(SmartGlassesForegroundService.ACTION_START);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(svc);
            } else {
                startService(svc);
            }
        } catch (Exception e) {
            Log.e("MainActivity", "Failed to start monitoring service", e);
        }
    }
    private void setupButtons() {
        btnPeopleRecognition.setOnClickListener(v -> {
            speak(StringResources.getString(Main.FACE_RECOGNITION_STARTING), StringResources.getCurrentLocale());
            updateStatus("Opening face recognition...");
            new android.os.Handler().postDelayed(() -> {
                startActivity(new Intent(this, EnhancedFaceRecognitionActivity.class));
            },1500);
        });



        btnVoiceCommand.setOnClickListener(v -> {
            toggleVoiceListening();
        });

        btnNavigation.setOnClickListener(v -> {
            stopListening();
            speak(StringResources.getString(Main.NAVIGATION_STARTING), StringResources.getCurrentLocale());
            updateStatus("Loading navigation...");

        });

        btnSettings.setOnClickListener(v -> {
            stopListening();
            speak(StringResources.getString(Main.SETTINGS_OPENING), StringResources.getCurrentLocale());
            updateStatus("Loading settings...");
            new android.os.Handler().postDelayed(() -> {
                startActivity(new Intent(this, SettingsActivity.class));
            }, 1500);
        });

        btnStopSmartGlasses.setOnClickListener(v->{
            stopSmartGlasses();
        });
    }

    private void addHapticFeedback() {
        View [] buttons = {btnPeopleRecognition,btnVoiceCommand,btnNavigation,btnSettings};
        for(View button:buttons) {
            button.setOnLongClickListener(v->{
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak(String.format(StringResources.getString(Main.BUTTON_TAP_ACTIVATE), buttonText), StringResources.LOCALE_SINHALA);
                return true;
            });
        }
    }

    private void toggleVoiceListening() {
        if(isListening){
            stopListening();
        } else {
            startListening();
        }
    }

    private void startListening(){
        if(!isListening){
            if (speechRecognizer == null) {
                Log.e("MainActivity", "Speech recognizer is null, reinitializing...");
                setupVoiceRecognition();
                if (speechRecognizer == null) {
                    updateStatus("Speech recognition not available");
                    speak("Speech recognition is not available", StringResources.getCurrentLocale());
                    return;
                }
            }
            
            try {
                isListening = true;
                updateStatus("Listening for commands...");
                speak(StringResources.getString(Main.VOICE_COMMAND_ACTIVATED), StringResources.getCurrentLocale());
                updateSpeechRecognitionLanguage();
                speechRecognizer.startListening(speechRecognizerIntent);
                btnVoiceCommand.setText("Stop listening");
                btnVoiceCommand.setBackgroundTintList(getColorStateList(android.R.color.holo_red_dark));
            } catch (Exception e) {
                Log.e("MainActivity", "Error starting speech recognition: " + e.getMessage());
                isListening = false;
                updateStatus("Error starting speech recognition");
                speak("Error starting speech recognition", StringResources.getCurrentLocale());
            }
        }
    }

    private void stopListening() {
        if (isListening) {
            isListening = false;
            try {
                if (speechRecognizer != null) {
                    speechRecognizer.stopListening();
                }
                updateStatus("Voice recognition stopped");
                btnVoiceCommand.setText("Voice Assistant");
                btnVoiceCommand.setBackgroundTintList(getColorStateList(android.R.color.holo_blue_bright));
            } catch (Exception e) {
                Log.e("MainActivity", "Error stopping speech recognition: " + e.getMessage());
                updateStatus("Error stopping speech recognition");
            }
        }
    }

    private void processVoiceCommand(String command){
        String lowerCommand = command.toLowerCase().trim();
        Log.d("VoiceCommand", "Received command: " + command);

        double faceMatchScore = calculateSimilarity(lowerCommand, "muhuna");
        double navMatchScore = calculateSimilarity(lowerCommand, "sanchalanaya");
        double settingsMatchScore = calculateSimilarity(lowerCommand, "sakesum");

        Log.d("VoiceCommand", "Face match score: " + faceMatchScore);
        Log.d("VoiceCommand", "Navigation match score: " + navMatchScore);
        Log.d("VoiceCommand", "Settings match score: " + settingsMatchScore);


        if(lowerCommand.equals("face") || lowerCommand.contains("people") ||
                lowerCommand.contains("recognition") || lowerCommand.contains("recognize") ||
                lowerCommand.contains("muhuna") || lowerCommand.contains("muhuṇa") ||
                lowerCommand.contains("mohana") || lowerCommand.contains("mohuna") ||
                lowerCommand.contains("මුහුණ") || lowerCommand.contains("හඳුනාගැනීම") ||
                lowerCommand.contains("handunaganeema") || lowerCommand.contains("handuna") ||
                lowerCommand.startsWith("muh") || lowerCommand.startsWith("moh")) {
            stopListening();
            speak(StringResources.getString(Main.OPENING_FACE_RECOGNITION), StringResources.getCurrentLocale());
            startActivity(new Intent(this,EnhancedFaceRecognitionActivity.class));

        } else if(lowerCommand.contains("navigation") || lowerCommand.contains("navigate") ||
                lowerCommand.contains("sanchalanaya") || lowerCommand.contains("සංචාලනය") ||
                lowerCommand.contains("sanchalan") || lowerCommand.contains("direction")) {
            stopListening();
            speak(StringResources.getString(Main.OPENING_NAVIGATION), StringResources.getCurrentLocale());

        } else if(lowerCommand.contains("settings") || lowerCommand.contains("setting") ||
                lowerCommand.contains("sakesum") || lowerCommand.contains("සැකසුම්") ||
                lowerCommand.contains("sakasuma") || lowerCommand.contains("config")) {
            stopListening();
            speak(StringResources.getString(Main.SETTINGS_OPENING), StringResources.getCurrentLocale());
            startActivity(new Intent(this, SettingsActivity.class));

        } else if(lowerCommand.contains("stop") || lowerCommand.contains("exit") ||
                lowerCommand.contains("navattanna") || lowerCommand.contains("නවත්වන්න") ||
                lowerCommand.contains("navatta") || lowerCommand.contains("thamba")) {

            speak(StringResources.getString(Main.STOPPING_VOICE_COMMANDS), StringResources.getCurrentLocale());
            stopListening();

        } else if(lowerCommand.contains("stop") || lowerCommand.contains("shutdown") || lowerCommand.contains("turn off")
                || lowerCommand.contains("stop smart glasses")) {
            stopListening();
            stopSmartGlasses();
        }else {
            Log.d("VoiceCommand", "Command not recognized: " + command);
            speak("Command not recognized. You said: " + command, StringResources.getCurrentLocale());

            speak("Try saying: face, navigation, settings, or stop", StringResources.getCurrentLocale());
        }
    }

    private void stopSmartGlasses(){
        speak("Stopping smart glasses...",StringResources.getCurrentLocale());
        updateStatus("Stopping smart glasses...");

        Intent stopIntent = new Intent(this, SmartGlassesForegroundService.class);
        stopIntent.setAction(SmartGlassesForegroundService.ACTION_COMPLETE_SHUTDOWN);
        startService(stopIntent);
    }

    private double calculateSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) return 0.0;

        int maxLength = Math.max(s1.length(), s2.length());
        if (maxLength == 0) return 1.0;

        int editDistance = levenshteinDistance(s1, s2);
        return 1.0 - ((double) editDistance / maxLength);
    }

    private int levenshteinDistance(String s1, String s2) {
        int[][] dp = new int[s1.length() + 1][s2.length() + 1];

        for (int i = 0; i <= s1.length(); i++) {
            dp[i][0] = i;
        }
        for (int j = 0; j <= s2.length(); j++) {
            dp[0][j] = j;
        }

        for (int i = 1; i <= s1.length(); i++) {
            for (int j = 1; j <= s2.length(); j++) {
                int cost = (s1.charAt(i-1) == s2.charAt(j-1)) ? 0 : 1;
                dp[i][j] = Math.min(Math.min(
                                dp[i-1][j] + 1,
                                dp[i][j-1] + 1),
                        dp[i-1][j-1] + cost
                );
            }
        }

        return dp[s1.length()][s2.length()];
    }
    private void updateStatus(String message) {
        statusText.setText(message);
        statusText.setContentDescription(message);
    }

    private void speak(String text) {
        speak(text, null);
    }

    private void speak(String text, Locale locale) {
        if(ttsEngine != null){
            if (locale != null && locale != ttsEngine.getLanguage()) {
                ttsEngine.setLanguage(locale);
            }
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "BLIND_ASSISTANT_UTTERANCE");
        }
    }

    @Override
    public void onReadyForSpeech(Bundle params) {
        updateStatus("Ready for speech...");
    }

    @Override
    public void onBeginningOfSpeech(){
        updateStatus("Listening...");
    }

    @Override
    public void onRmsChanged(float rmsdB) {

    }

    @Override
    public void onBufferReceived(byte[] buffer) {}

    @Override
    public void onEndOfSpeech() {
        updateStatus("Processing speech...");
    }

    @Override
    public void onError(int error) {
        String errorMessage;
        Log.e("MainActivity", "Speech recognition error: " + error);
        
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                errorMessage = StringResources.getString(Main.ERROR_AUDIO);
                Log.e("MainActivity", "Audio recording error");
                break;
            case SpeechRecognizer.ERROR_CLIENT:
                errorMessage = StringResources.getString(Main.ERROR_CLIENT);
                Log.e("MainActivity", "Client side error");
                break;
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                errorMessage = StringResources.getString(Main.ERROR_INSUFFICIENT_PERMISSIONS);
                Log.e("MainActivity", "Insufficient permissions");
                break;
            case SpeechRecognizer.ERROR_NETWORK:
                errorMessage = StringResources.getString(Main.ERROR_NETWORK);
                Log.e("MainActivity", "Network error");
                break;
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                errorMessage = StringResources.getString(Main.ERROR_NETWORK_TIMEOUT);
                Log.e("MainActivity", "Network timeout");
                break;
            case SpeechRecognizer.ERROR_NO_MATCH:
                errorMessage = StringResources.getString(Main.ERROR_NO_MATCH);
                Log.d("MainActivity", "No speech match found");
                break;
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                errorMessage = StringResources.getString(Main.ERROR_RECOGNIZER_BUSY);
                Log.e("MainActivity", "Speech recognizer busy");
                break;
            case SpeechRecognizer.ERROR_SERVER:
                errorMessage = StringResources.getString(Main.ERROR_SERVER);
                Log.e("MainActivity", "Server error");
                break;
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                errorMessage = StringResources.getString(Main.ERROR_SPEECH_TIMEOUT);
                Log.d("MainActivity", "Speech timeout");
                break;
            default:
                errorMessage = "Speech recognition error: " + error;
                Log.e("MainActivity", "Unknown speech recognition error: " + error);
                break;
        }

        updateStatus(errorMessage);
        speak(errorMessage);
        isListening = false;
        btnVoiceCommand.setText("Voice Assistant");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            btnVoiceCommand.setBackgroundTintList(getColorStateList(android.R.color.holo_blue_bright));
        }
    }

    public void onResults(Bundle results){
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        float[] confidenceScores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);

        if(matches != null && !matches.isEmpty()){

            String recognizedText = matches.get(0);
            Log.d("VoiceCommand", "Raw matches: " + matches.toString());

            try {
                String logMessage = new String(recognizedText.getBytes("UTF-8"), "UTF-8");
                Log.d("VoiceCommand", "Recognized Sinhala: " + logMessage);
            } catch (UnsupportedEncodingException e) {
                Log.e("VoiceCommand", "Encoding error: " + e.getMessage());
            }

            updateStatus("recognized text: " + recognizedText);
            processVoiceCommand(recognizedText);
        }

        if(isListening){
            new android.os.Handler().postDelayed(()->{
                if(isListening){
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            },2000);
        }
    }

    @Override
    public void onPartialResults(Bundle partialResults){
        ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if(matches != null && !matches.isEmpty()){
            updateStatus("Hearing: " + matches.get(0));
        }
    }

    @Override
    public void onEvent(int eventType,Bundle params){}

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            Locale currentLocale = StringResources.getCurrentLocale();
            int result = ttsEngine.setLanguage(currentLocale);
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                updateStatus("TTS Language not supported");

                ttsEngine.setLanguage(Locale.US);
            } else {
                new android.os.Handler().postDelayed(() -> {
                    startListening();
                }, 2000);
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_RECORD_AUDIO) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                setupVoiceRecognition();
            } else {
                speak(StringResources.getString(Main.MIC_PERMISSION_REQUIRED), StringResources.LOCALE_SINHALA);
            }
        }
        if (requestCode == PERMISSION_REQUEST_NOTIFICATIONS) {
            // No-op; foreground service still shows ongoing notification if denied
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }
        if(speechRecognizer != null){
            try {
                speechRecognizer.stopListening();
                speechRecognizer.destroy();
            } catch (Exception e) {
                Log.e("MainActivity", "Error destroying speech recognizer: " + e.getMessage());
            }
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if(isListening){
            stopListening();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadSavedLanguagePreference();
        if(speechRecognizer != null){
            updateSpeechRecognitionLanguage();
        }
        if (ttsEngine != null && !isListening) {
            new android.os.Handler().postDelayed(() -> {
                startListening();
            }, 1000);
        }

        try {
            getSharedPreferences("blind_assistant_prefs", MODE_PRIVATE)
                    .edit().putBoolean("ui_recognition_active", false).apply();
        } catch (Exception ignored) {}
    }
}