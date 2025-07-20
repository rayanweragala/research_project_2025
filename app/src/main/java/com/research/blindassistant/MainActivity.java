package com.research.blindassistant;

import android.content.Intent;
import android.os.Bundle;

import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import java.util.Locale;

public class MainActivity extends AppCompatActivity implements TextToSpeech.OnInitListener {

    private Button btnPeopleRecognition,btnVoiceCommand,btnNavigation,btnSettings;
    private TextView statusText;

    private TextToSpeech ttsEngine;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        ttsEngine = new TextToSpeech(this, this);
        initializeComponents();
        setupButtons();

        speak("Assistant ready. select a function");
    }

    private void initializeComponents() {
        btnPeopleRecognition = findViewById(R.id.btnPeopleRecognition);
        btnVoiceCommand = findViewById(R.id.btnVoiceCommand);
        btnNavigation = findViewById(R.id.btnNavigation);
        btnSettings = findViewById(R.id.btnSettings);
        statusText = findViewById(R.id.statusText);
    }

    private void setupButtons() {
        btnPeopleRecognition.setOnClickListener(v -> {
            speak("starting people recognition");
            updateStatus("initializing people recognition.....");
            startActivity(new Intent(this,PeopleRecognitionActivity.class));
        });

        btnVoiceCommand.setOnClickListener(v -> {
            speak("Voice command activated. Speak now.");
            updateStatus("Listening for commands...");
        });

        btnNavigation.setOnClickListener(v -> {
            speak("Navigation assistance starting");
            updateStatus("Loading navigation...");
        });

        btnSettings.setOnClickListener(v -> {
            speak("Opening settings");
            updateStatus("Loading settings...");
        });

    }

    private void addHapticFeedback(View view) {
        view.setOnLongClickListener(v -> {
            v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
            speak("Button: " + ((Button) v).getText().toString());
            return true;
        });
    }

    private void updateStatus(String message) {
        statusText.setText(message);
    }

    private void speak(String text) {
        if(ttsEngine != null) {
            ttsEngine.speak(text,TextToSpeech.QUEUE_FLUSH,null,"BLIND_ASSISTANT_UTTERANCE");
        }
    }

    @Override
    public void onInit(int status) {
        if(status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.US);
            if(result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if(ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }
    }
}