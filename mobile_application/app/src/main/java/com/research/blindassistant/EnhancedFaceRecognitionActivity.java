package com.research.blindassistant;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Locale;

import static com.research.blindassistant.StringResources.FaceRecognition;

public class EnhancedFaceRecognitionActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener, RecognitionListener {

    private static final String TAG = "EnhancedFaceRec";
    private static final int AUDIO_PERMISSION_REQUEST = 100;
    private static final String SERVER_URL = "http://10.72.250.126:5000";

    private TextView statusText, resultsText, instructionsText, performanceText;
    private Button btnStartRecognition, btnStopRecognition, btnBack, btnAddFriend;
    private ImageView statusIndicator, cameraFeedView;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private RequestQueue requestQueue;
    private Handler mainHandler;

    private boolean isRecognizing = false;
    private boolean isListening = false;
    private boolean serverConnected = false;
    private boolean serverCameraActive = false;

    private int totalFramesReceived = 0;
    private int framesWithFaces = 0;
    private int multiPersonDetections = 0;
    private int successfulRecognitions = 0;

    private long lastRecognitionTime = 0;
    private long lastSpeechTime = 0;
    private final int FRAME_REQUEST_INTERVAL = 500;
    private final int SPEECH_INTERVAL = 3000;

    private StatusManager statusManager;
    private String lastSpokenMessage = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_enhanced_face_recognition);

        statusManager = new StatusManager(this);
        statusManager.updateStatus(StatusManager.ConnectionStatus.DISCONNECTED,
                "Smart Glasses Disconnected", "Connecting to server...");

        initializeComponents();
        checkPermissions();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        requestQueue = Volley.newRequestQueue(this);
        mainHandler = new Handler(Looper.getMainLooper());

        testServerConnection();
        speak(StringResources.getString(FaceRecognition.SMART_GLASSES_READY));
    }

    private void initializeComponents() {
        statusText = findViewById(R.id.statusText);
        resultsText = findViewById(R.id.resultsText);
        instructionsText = findViewById(R.id.instructionsText);
        performanceText = findViewById(R.id.performanceText);
        btnStartRecognition = findViewById(R.id.btnStartRecognition);
        btnStopRecognition = findViewById(R.id.btnStopRecognition);
        btnBack = findViewById(R.id.btnBack);
        btnAddFriend = findViewById(R.id.btnAddFriend);
        statusIndicator = findViewById(R.id.statusIndicator);
        cameraFeedView = findViewById(R.id.cameraFeedView);

        updateInstructions("Connecting to smart glasses camera server...");
        ttsEngine = new TextToSpeech(this, this);
    }

    private void checkPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO},
                    AUDIO_PERMISSION_REQUEST);
        }
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
            speak(StringResources.getString(FaceRecognition.BACK_TO_MAIN));
            finish();
        });
        btnAddFriend.setOnClickListener(v -> {
            speak(StringResources.getString(FaceRecognition.OPENING_REGISTRATION));
            startActivity(new Intent(this, AddFriendActivity.class));
        });
    }

    private void addHapticFeedback() {
        View[] buttons = {btnStartRecognition, btnStopRecognition, btnBack, btnAddFriend};
        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak(String.format(StringResources.getString(FaceRecognition.BUTTON_PREFIX), buttonText));
                return true;
            });
        }
    }

    private void testServerConnection() {
        String url = SERVER_URL + "/api/health";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        String status = response.getString("status");
                        if ("healthy".equals(status)) {
                            serverConnected = true;
                            int peopleCount = response.getInt("people_count");
                            boolean cameraActive = response.optBoolean("camera_active", false);

                            if (cameraActive) {
                                serverCameraActive = true;
                                statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                                        "Smart Glasses Connected",
                                        String.format("Multi-face recognition ready • %d people registered", peopleCount));
                                speak(String.format("Smart glasses connected with multi-face recognition. %d people registered", peopleCount));
                                updateInstructions("Say 'START' to begin recognition or 'ADD FRIEND' to register new people");
                            } else {
                                statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTING,
                                        "Server Connected", "Starting camera system...");
                                startServerCamera();
                            }
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing server response", e);
                        handleServerError("Invalid server response");
                    }
                },
                error -> {
                    Log.e(TAG, "Server connection failed", error);
                    handleServerError("Cannot connect to smart glasses server");
                });

        requestQueue.add(request);
    }

    private void startServerCamera() {
        String url = SERVER_URL + "/api/camera/start";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.POST, url, null,
                response -> {
                    try {
                        boolean success = response.getBoolean("success");
                        if (success) {
                            serverCameraActive = true;
                            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                                    "Smart Glasses Ready", "Multi-face recognition active");
                            speak("Camera activated with multi-face recognition");
                            updateInstructions("Say 'START' to begin or 'ADD FRIEND' to register people");
                        } else {
                            handleServerError("Failed to start camera");
                        }
                    } catch (JSONException e) {
                        handleServerError("Camera activation error");
                    }
                },
                error -> handleServerError("Could not activate camera"));

        requestQueue.add(request);
    }

    private void handleServerError(String message) {
        serverConnected = false;
        serverCameraActive = false;
        statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR, "Connection Failed", message);
        updateInstructions(message);
        speak(message);
    }

    private void startRecognition() {
        if (!serverConnected || !serverCameraActive) {
            speak("Smart glasses not ready. Please wait.");
            return;
        }

        if (isRecognizing) return;

        isRecognizing = true;

        btnStartRecognition.setVisibility(View.GONE);
        btnStopRecognition.setVisibility(View.VISIBLE);
        statusIndicator.setImageResource(R.drawable.ic_visibility_on);

        statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                "Recognition Active", "Multi-face detection enabled");
        updateResults("Analyzing camera feed with multi-face AI...");
        updateInstructions("Recognition active. Multiple people will be identified simultaneously.");
        speak("Multi-face recognition started");

        startVoiceListening();
        resetPerformanceStats();
        startFrameProcessing();
    }

    private void stopRecognition() {
        if (isRecognizing) {
            isRecognizing = false;

            btnStartRecognition.setVisibility(View.VISIBLE);
            btnStopRecognition.setVisibility(View.GONE);

            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                    "Smart Glasses Ready", "Recognition stopped");
            updateInstructions("Say 'START' to begin or 'ADD FRIEND' to register");
            speak("Recognition stopped");

            stopVoiceListening();
            showPerformanceStats();
        }
    }

    private void startFrameProcessing() {
        mainHandler.post(new Runnable() {
            @Override
            public void run() {
                if (isRecognizing) {
                    requestFrameFromServer();
                    mainHandler.postDelayed(this, FRAME_REQUEST_INTERVAL);
                }
            }
        });
    }

    private void requestFrameFromServer() {
        if (!serverCameraActive || !isRecognizing) return;

        String url = SERVER_URL + "/api/camera/frame";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        totalFramesReceived++;

                        if (response.has("error")) {
                            updateResults("⚠️ " + response.getString("error"));
                            return;
                        }

                        if (response.has("image")) {
                            displayFrame(response.getString("image"));
                        }

                        processMultiFaceResult(response);

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing frame response", e);
                    }
                },
                error -> {
                    Log.e(TAG, "Frame request error", error);
                    if (isRecognizing) {
                        updateResults("⚠️ Connection interrupted");
                    }
                });

        request.setRetryPolicy(new com.android.volley.DefaultRetryPolicy(3000, 0, 0));
        requestQueue.add(request);
    }

    private void processMultiFaceResult(JSONObject response) {
        try {
            int faceCount = response.optInt("face_count", 0);
            int recognizedCount = response.optInt("recognized_count", 0);
            int unknownCount = response.optInt("unknown_count", 0);
            String message = response.optString("message", "Processing...");
            boolean recognized = response.optBoolean("recognized", false);
            double processingTime = response.optDouble("processing_time", 0.0);

            if (faceCount > 0) {
                framesWithFaces++;

                if (faceCount > 1) {
                    multiPersonDetections++;
                }

                if (recognized) {
                    successfulRecognitions++;
                }

                StringBuilder resultBuilder = new StringBuilder();
                resultBuilder.append(String.format("👥 %d %s detected\n",
                        faceCount, faceCount == 1 ? "person" : "people"));

                if (recognizedCount > 0) {
                    resultBuilder.append(String.format("✅ %d recognized\n", recognizedCount));
                }
                if (unknownCount > 0) {
                    resultBuilder.append(String.format("❓ %d unknown\n", unknownCount));
                }

                resultBuilder.append(String.format("\n%s", message));
                resultBuilder.append(String.format("\n⚡ Processing: %.0fms", processingTime * 1000));

                if (response.has("faces")) {
                    JSONArray faces = response.getJSONArray("faces");
                    resultBuilder.append("\n\n📋 Details:");

                    for (int i = 0; i < faces.length(); i++) {
                        JSONObject face = faces.getJSONObject(i);
                        boolean faceRecognized = face.optBoolean("recognized", false);

                        if (faceRecognized) {
                            String name = face.optString("name", "Unknown");
                            double confidence = face.optDouble("confidence", 0.0);
                            String confLevel = face.optString("confidence_level", "medium");

                            resultBuilder.append(String.format("\n  • %s (%.1f%% - %s)",
                                    name, confidence * 100, confLevel));
                        } else {
                            resultBuilder.append(String.format("\n  • Unknown person %d", i + 1));
                        }
                    }
                }

                updateResults(resultBuilder.toString());

                long currentTime = System.currentTimeMillis();
                if (currentTime - lastSpeechTime > SPEECH_INTERVAL) {
                    if (!message.equals(lastSpokenMessage)) {
                        speak(message);
                        lastSpokenMessage = message;
                        lastSpeechTime = currentTime;
                    }
                }

            } else {
                updateResults("👁️ No faces detected\nProcessing: " + (int)(processingTime * 1000) + "ms");
            }

            updatePerformanceDisplay();

        } catch (JSONException e) {
            Log.e(TAG, "Error processing multi-face result", e);
        }
    }

    private void displayFrame(String imageBase64) {
        try {
            byte[] imageBytes = android.util.Base64.decode(imageBase64, android.util.Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);

            if (bitmap != null) {
                mainHandler.post(() -> {
                    cameraFeedView.setImageBitmap(bitmap);
                    findViewById(R.id.noFeedMessage).setVisibility(View.GONE);
                });
            }
        } catch (Exception e) {
            Log.e(TAG, "Error displaying frame", e);
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
        } else if (lowerCommand.contains("add friend") || lowerCommand.contains("register")) {
            speak("Opening face registration");
            startActivity(new Intent(this, AddFriendActivity.class));
        } else if (lowerCommand.contains("back")) {
            speak("Going back");
            finish();
        } else if (lowerCommand.contains("stats")) {
            showPerformanceStats();
        }
    }

    private void resetPerformanceStats() {
        totalFramesReceived = 0;
        framesWithFaces = 0;
        multiPersonDetections = 0;
        successfulRecognitions = 0;
        lastRecognitionTime = 0;
        lastSpeechTime = 0;
        lastSpokenMessage = "";
    }

    private void updatePerformanceDisplay() {
        if (performanceText == null) return;

        float faceDetectionRate = totalFramesReceived > 0 ?
                (float) framesWithFaces / totalFramesReceived * 100 : 0;

        String performance = String.format(
                "📊 Frames: %d | With faces: %d (%.1f%%) | Multi-person: %d | Recognized: %d",
                totalFramesReceived, framesWithFaces, faceDetectionRate,
                multiPersonDetections, successfulRecognitions
        );

        performanceText.setText(performance);
    }

    private void showPerformanceStats() {
        String statsMessage = String.format(
                "Performance: Processed %d frames, %d with faces, %d multi-person detections, %d successful recognitions",
                totalFramesReceived, framesWithFaces, multiPersonDetections, successfulRecognitions
        );

        speak(statsMessage);
        updateResults("📊 " + statsMessage);
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

    private void speak(String text) {
        if (ttsEngine != null) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "MULTI_FACE_UTTERANCE");
        }
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches != null && !matches.isEmpty()) {
            processVoiceCommand(matches.get(0));
        }

        if (isListening && isRecognizing) {
            mainHandler.postDelayed(() -> {
                if (isListening && isRecognizing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override
    public void onError(int error) {
        if (error != SpeechRecognizer.ERROR_NO_MATCH && isListening) {
            mainHandler.postDelayed(() -> {
                if (isListening && isRecognizing) {
                    speechRecognizer.startListening(speechRecognizerIntent);
                }
            }, 1000);
        }
    }

    @Override public void onReadyForSpeech(Bundle params) {}
    @Override public void onBeginningOfSpeech() {}
    @Override public void onRmsChanged(float rmsdB) {}
    @Override public void onBufferReceived(byte[] buffer) {}
    @Override public void onEndOfSpeech() {}
    @Override public void onPartialResults(Bundle partialResults) {}
    @Override public void onEvent(int eventType, Bundle params) {}

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            ttsEngine.setLanguage(Locale.US);
            mainHandler.postDelayed(() -> {
                if (!isRecognizing) {
                    startVoiceListening();
                }
            }, 1000);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isRecognizing) {
            stopRecognition();
        }
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
        if (isRecognizing) {
            stopRecognition();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (serverConnected && !isRecognizing) {
            testServerConnection();
        }
    }
}