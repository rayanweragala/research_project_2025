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
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;
import java.util.Locale;

import static com.research.blindassistant.StringResources.Main;

public class MainActivity extends AppCompatActivity implements TextToSpeech.OnInitListener,RecognitionListener {

    private Button btnPeopleRecognition,btnVoiceCommand,btnNavigation,btnSettings;
    private TextView statusText;
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private boolean isListening = false;
    private static final int PERMISSION_REQUEST_RECORD_AUDIO = 1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        ttsEngine = new TextToSpeech(this, this);
        initializeComponents();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        speak(StringResources.getString(Main.ASSISTANT_READY), StringResources.getCurrentLocale());
    }
    private void initializeComponents() {
        btnPeopleRecognition = findViewById(R.id.btnPeopleRecognition);
        btnVoiceCommand = findViewById(R.id.btnVoiceCommand);
        btnNavigation = findViewById(R.id.btnNavigation);
        btnSettings = findViewById(R.id.btnSettings);
        statusText = findViewById(R.id.statusText);
    }

    private void setupVoiceRecognition() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO}, PERMISSION_REQUEST_RECORD_AUDIO);
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener((RecognitionListener) this);

        speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);

        Locale currentLocale = StringResources.getCurrentLocale();
        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, currentLocale.toString());

        if (currentLocale.equals(StringResources.LOCALE_SINHALA)) {
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "si-LK");
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "si-LK");
        }

        speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
    }
    private void setupButtons() {
        btnPeopleRecognition.setOnClickListener(v -> {
            speak(StringResources.getString(Main.FACE_RECOGNITION_STARTING), StringResources.getCurrentLocale());
            updateStatus("Opening face recognition...");
            startActivity(new Intent(this, EnhancedFaceRecognitionActivity.class));
        });

        btnVoiceCommand.setOnClickListener(v -> {
            toggleVoiceListening();
        });

        btnNavigation.setOnClickListener(v -> {
            speak(StringResources.getString(Main.NAVIGATION_STARTING), StringResources.getCurrentLocale());
            updateStatus("Loading navigation...");

        });

        btnSettings.setOnClickListener(v -> {
            speak(StringResources.getString(Main.SETTINGS_OPENING), StringResources.getCurrentLocale());
            updateStatus("Loading settings...");
            startActivity(new Intent(this, SettingsActivity.class));
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
            isListening = true;
            updateStatus("Listening for commands...");
            speak(StringResources.getString(Main.VOICE_COMMAND_ACTIVATED), StringResources.getCurrentLocale());
            speechRecognizer.startListening(speechRecognizerIntent);
            btnVoiceCommand.setText("Stop listening");
            btnVoiceCommand.setBackgroundTintList(getColorStateList(android.R.color.holo_red_dark));
        }
    }

    private void stopListening() {
        if (isListening) {
            isListening = false;
            speechRecognizer.stopListening();
            updateStatus("Voice recognition stopped");
            btnVoiceCommand.setText("Voice Assistant");
            btnVoiceCommand.setBackgroundTintList(getColorStateList(android.R.color.holo_blue_bright));
        }
    }

    private void processVoiceCommand(String command){
        String lowerCommand = command.toLowerCase().trim();

        if(lowerCommand.equals("face") || lowerCommand.contains("people") ||
        lowerCommand.contains("recognition") || lowerCommand.contains("recognize")){
            speak(StringResources.getString(Main.OPENING_FACE_RECOGNITION), StringResources.LOCALE_SINHALA);
            startActivity(new Intent(this,EnhancedFaceRecognitionActivity.class));
        } else if(lowerCommand.contains("navigation") || lowerCommand.contains("navigate")){
            speak(StringResources.getString(Main.OPENING_NAVIGATION), StringResources.LOCALE_SINHALA);
        } else if(lowerCommand.contains("settings") || lowerCommand.contains("setting")){
            speak(StringResources.getString(Main.SETTINGS_OPENING), StringResources.LOCALE_SINHALA);
        } else if(lowerCommand.contains("stop") || lowerCommand.contains("exit")){
            speak(StringResources.getString(Main.STOPPING_VOICE_COMMANDS), StringResources.LOCALE_SINHALA);
            stopListening();
        } else {
            speak(StringResources.getString(Main.COMMAND_NOT_RECOGNIZED), StringResources.LOCALE_SINHALA);
        }
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
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                errorMessage = StringResources.getString(Main.ERROR_AUDIO);
                break;
            case SpeechRecognizer.ERROR_CLIENT:
                errorMessage = StringResources.getString(Main.ERROR_CLIENT);
                break;
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                errorMessage = StringResources.getString(Main.ERROR_INSUFFICIENT_PERMISSIONS);
                break;
            case SpeechRecognizer.ERROR_NETWORK:
                errorMessage = StringResources.getString(Main.ERROR_NETWORK);
                break;
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                errorMessage = StringResources.getString(Main.ERROR_NETWORK_TIMEOUT);
                break;
            case SpeechRecognizer.ERROR_NO_MATCH:
                errorMessage = StringResources.getString(Main.ERROR_NO_MATCH);
                break;
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                errorMessage = StringResources.getString(Main.ERROR_RECOGNIZER_BUSY);
                break;
            case SpeechRecognizer.ERROR_SERVER:
                errorMessage = StringResources.getString(Main.ERROR_SERVER);
                break;
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                errorMessage = StringResources.getString(Main.ERROR_SPEECH_TIMEOUT);
                break;
            default:
                errorMessage = "Speech recognition error";
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
        if(matches != null && !matches.isEmpty()){
            String recognizedText = matches.get(0);
            updateStatus("Recognized: " + recognizedText);
            processVoiceCommand(recognizedText);
        }

        if(isListening){
            new android.os.Handler().postDelayed(()->{
                if(isListening){
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            },1000);
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
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }
        if(speechRecognizer != null){
            speechRecognizer.destroy();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if(isListening){
            speechRecognizer.stopListening();
        }
    }
}