package com.research.blindassistant;

import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.util.Locale;

public class PeopleRecognitionActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener {

    private TextView statusText, resultsText;
    private Button btnStartRecognition, btnStopRecognition, btnBack;
    private TextToSpeech ttsEngine;
    private boolean isRecognizing = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_people_recognition);

        ttsEngine = new TextToSpeech(this, this);

        initializeComponents();
        setupButtons();
        speak("Ready for people recognition. Press start to begin.");
    }

    protected void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        resultsText = findViewById(R.id.resultsText);
        btnStartRecognition = findViewById(R.id.btnStartRecognition);
        btnStopRecognition = findViewById(R.id.btnStopRecognition);
        btnBack = findViewById(R.id.btnBack);
    }

    private void setupButtons() {
        btnStartRecognition.setOnClickListener(v -> startRecognition());
        btnStopRecognition.setOnClickListener(v -> stopRecognition());
        btnBack.setOnClickListener(v -> finish());
    }

    private void startRecognition() {
        if (!isRecognizing) {
            isRecognizing = true;
            btnStartRecognition.setVisibility(View.GONE);
            btnStopRecognition.setVisibility(View.VISIBLE);

            updateStatus("Analyzing...");
            updateResults("Listening through smart glasses");
            speak("Recognition started. Analyzing smart glasses feed.");

            simulateRecognition();
        }
    }

    private void stopRecognition() {
        if (isRecognizing) {
            isRecognizing = false;
            btnStartRecognition.setVisibility(View.VISIBLE);
            btnStopRecognition.setVisibility(View.GONE);

            updateStatus("Recognition Stopped");
            updateResults("Press start to begin again");
            speak("Recognition stopped");
        }
    }

    private void simulateRecognition() {
        new android.os.Handler().postDelayed(() -> {
            if (isRecognizing) {
                String result = "John detected 2 meters ahead";
                updateResults(result);
                speak(result);
            }
        }, 3000);
    }

    private void updateStatus(String message) {
        statusText.setText(message);
    }

    private void updateResults(String results) {
        resultsText.setText(results);
    }

    private void speak(String text) {
        if (ttsEngine != null) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "BLIND_ASSISTANT_UTTERANCE");
        }
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = ttsEngine.setLanguage(Locale.US);
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
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
    }
}