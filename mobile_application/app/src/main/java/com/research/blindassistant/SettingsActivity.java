package com.research.blindassistant;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;
import java.util.Locale;

public class SettingsActivity extends AppCompatActivity implements TextToSpeech.OnInitListener {

    private TextView titleText;
    private TextView languageSelectionText;
    private RadioGroup languageRadioGroup;
    private RadioButton englishRadioButton;
    private RadioButton sinhalaRadioButton;
    private Button backButton;
    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private boolean isListening = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        ttsEngine = new TextToSpeech(this, this);
        
        initializeComponents();
        setupLanguageSelection();
        setupBackButton();
        addHapticFeedback();
        setupVoiceRecognition();
    }

    private void initializeComponents() {
        titleText = findViewById(R.id.settingsTitleText);
        languageSelectionText = findViewById(R.id.languageSelectionText);
        languageRadioGroup = findViewById(R.id.languageRadioGroup);
        englishRadioButton = findViewById(R.id.englishRadioButton);
        sinhalaRadioButton = findViewById(R.id.sinhalaRadioButton);
        backButton = findViewById(R.id.backButton);
    }

    private void setupVoiceRecognition() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override
                public void onResults(Bundle results) {
                    ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                    if (matches != null && !matches.isEmpty()) {
                        processVoiceCommand(matches.get(0));
                    }
                }

                @Override public void onReadyForSpeech(Bundle params) {}
                @Override public void onBeginningOfSpeech() {}
                @Override public void onRmsChanged(float rmsdB) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {}
                @Override
                public void onError(int error) {
                    isListening = false;
                    if (error != SpeechRecognizer.ERROR_NO_MATCH && error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
                       new Handler().postDelayed(() -> startListening(), 2000);
                    } else {
                        new Handler().postDelayed(() -> startListening(), 1000);
                    }
                }
                @Override public void onPartialResults(Bundle partialResults) {}
                @Override public void onEvent(int eventType, Bundle params) {}
            });

            speechRecognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
        }
    }

    private void startListening() {
        if (speechRecognizer != null && !isListening) {
            isListening = true;
            Locale currentLocale = StringResources.getCurrentLocale();
            speechRecognizerIntent.removeExtra(RecognizerIntent.EXTRA_LANGUAGE);
            if (currentLocale.equals(StringResources.LOCALE_SINHALA)) {
                speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "si-LK");
            } else {
                speechRecognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US");
            }
            try {
                speechRecognizer.startListening(speechRecognizerIntent);
            } catch (Exception e) {
                isListening = false;
                new Handler().postDelayed(() -> startListening(), 2000);
            }
        }
    }

    private void processVoiceCommand(String command) {
        String lowerCommand = command.toLowerCase().trim();

        Log.e("SettingsVoice", "Recognized command: " + command);

        if (lowerCommand.contains("english") || lowerCommand.contains("ingirisi") ||
                lowerCommand.contains("ඉංග්‍රීසි") || lowerCommand.contains("ingris")) {

            speak("English selected", StringResources.LOCALE_ENGLISH);
            englishRadioButton.setChecked(true);

        } else if (lowerCommand.contains("sinhala") || lowerCommand.contains("සිංහල") ||
                lowerCommand.contains("sinhal") || lowerCommand.contains("sinh")) {

            speak("සිංහල තෝරාගන්නා ලදි", StringResources.LOCALE_SINHALA);
            sinhalaRadioButton.setChecked(true);

        } else if (lowerCommand.contains("back") || lowerCommand.contains("return") ||
                lowerCommand.contains("yanawa") || lowerCommand.contains("යනවා") ||
                lowerCommand.contains("yana") || lowerCommand.contains("go back")) {

            speak("Going back", StringResources.getCurrentLocale());
            finish();
            return;
        }

        isListening = false;
        new Handler().postDelayed(this::startListening, 1500);
    }

    private void setupLanguageSelection() {
        Locale savedLocale = getSavedLanguagePreference();
        StringResources.setLocale(savedLocale);

        if (savedLocale.equals(StringResources.LOCALE_SINHALA)) {
            sinhalaRadioButton.setChecked(true);
        } else {
            englishRadioButton.setChecked(true);
        }

        languageRadioGroup.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.englishRadioButton) {
                StringResources.setLocale(StringResources.LOCALE_ENGLISH);
                saveLanguagePreference(StringResources.LOCALE_ENGLISH);
                speak("Language set to English", StringResources.LOCALE_ENGLISH);
            } else if (checkedId == R.id.sinhalaRadioButton) {
                StringResources.setLocale(StringResources.LOCALE_SINHALA);
                saveLanguagePreference(StringResources.LOCALE_SINHALA);
                speak("භාෂාව සිංහල ලෙස සකසා ඇත", StringResources.LOCALE_SINHALA);
            }
        });
    }

    private void setupBackButton() {
        backButton.setOnClickListener(v -> {
            speak(StringResources.getString("settings_back_to_main"), StringResources.getCurrentLocale());
            finish();
        });
    }

    private void addHapticFeedback() {
        View[] views = {englishRadioButton, sinhalaRadioButton, backButton};
        for (View view : views) {
            view.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                if (v == englishRadioButton) {
                    speak("English language option. Tap to select.", StringResources.LOCALE_ENGLISH);
                } else if (v == sinhalaRadioButton) {
                    speak("සිංහල භාෂා විකල්පය. තේරීමට තට්ටු කරන්න.", StringResources.LOCALE_SINHALA);
                } else if (v == backButton) {
                    speak(StringResources.getString("back_button_desc"), StringResources.getCurrentLocale());
                }
                return true;
            });
        }
    }

    private void saveLanguagePreference(Locale locale) {
        getSharedPreferences("blind_assistant_prefs", MODE_PRIVATE)
                .edit()
                .putString("selected_language", locale.getLanguage())
                .apply();
    }

    private Locale getSavedLanguagePreference() {
        String langCode = getSharedPreferences("blind_assistant_prefs", MODE_PRIVATE)
                .getString("selected_language", "en");
        return langCode.equals("si") ? StringResources.LOCALE_SINHALA : StringResources.LOCALE_ENGLISH;
    }

    private void speak(String text) {
        speak(text, null);
    }

    private void speak(String text, Locale locale) {
        if (ttsEngine != null) {
            if (locale != null && !locale.equals(ttsEngine.getLanguage())) {
                ttsEngine.setLanguage(locale);
            }
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "BLIND_ASSISTANT_SETTINGS_UTTERANCE");
        }
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            ttsEngine.setLanguage(StringResources.getCurrentLocale());
            speak(StringResources.getString("settings_screen_open"), StringResources.getCurrentLocale());
            new Handler().postDelayed(() -> {
                startListening();
            }, 2000);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ttsEngine != null) {
            ttsEngine.stop();
            ttsEngine.shutdown();
        }
        if(speechRecognizer != null) {
            speechRecognizer.stopListening();
            speechRecognizer.destroy();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (isListening && speechRecognizer != null) {
            speechRecognizer.stopListening();
            isListening = false;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (speechRecognizer != null && !isListening) {
            new Handler().postDelayed(this::startListening, 1000);
        }
    }
}