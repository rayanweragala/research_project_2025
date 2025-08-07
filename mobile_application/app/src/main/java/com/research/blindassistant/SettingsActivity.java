package com.research.blindassistant;

import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.Button;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

import java.util.Locale;

public class SettingsActivity extends AppCompatActivity implements TextToSpeech.OnInitListener {

    private TextView titleText;
    private TextView languageSelectionText;
    private RadioGroup languageRadioGroup;
    private RadioButton englishRadioButton;
    private RadioButton sinhalaRadioButton;
    private Button backButton;
    private TextToSpeech ttsEngine;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        ttsEngine = new TextToSpeech(this, this);
        
        initializeComponents();
        setupLanguageSelection();
        setupBackButton();
        addHapticFeedback();
    }

    private void initializeComponents() {
        titleText = findViewById(R.id.settingsTitleText);
        languageSelectionText = findViewById(R.id.languageSelectionText);
        languageRadioGroup = findViewById(R.id.languageRadioGroup);
        englishRadioButton = findViewById(R.id.englishRadioButton);
        sinhalaRadioButton = findViewById(R.id.sinhalaRadioButton);
        backButton = findViewById(R.id.backButton);
    }

    private void setupLanguageSelection() {
        Locale currentLocale = StringResources.getCurrentLocale();
        if (currentLocale.equals(StringResources.LOCALE_SINHALA)) {
            sinhalaRadioButton.setChecked(true);
        } else {
            englishRadioButton.setChecked(true);
        }

        languageRadioGroup.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.englishRadioButton) {
                StringResources.setLocale(StringResources.LOCALE_ENGLISH);
                speak("Language set to English", StringResources.LOCALE_ENGLISH);
            } else if (checkedId == R.id.sinhalaRadioButton) {
                StringResources.setLocale(StringResources.LOCALE_SINHALA);
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