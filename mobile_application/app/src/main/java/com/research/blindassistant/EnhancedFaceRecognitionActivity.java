package com.research.blindassistant;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.hardware.Camera;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.util.Base64;
import android.util.Log;

import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.research.blindassistant.StringResources.FaceRecognition;

public class EnhancedFaceRecognitionActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener, RecognitionListener {

    private static final String TAG = "EnhancedFaceRecognition";
    private static final int AUDIO_PERMISSION_REQUEST = 100;
    private static final String SERVER_URL = "http://10.187.202.95:5000";

    private TextView statusText, resultsText, instructionsText, performanceText;
    private Button btnStartRecognition, btnStopRecognition, btnBack, btnAddFriend;
    private ImageView statusIndicator, cameraFeedView;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private LocalFaceDetector localFaceDetector;
    private RequestQueue requestQueue;
    private ExecutorService executorService;
    private Handler mainHandler;

    private boolean isRecognizing = false;
    private boolean isListening = false;
    private boolean serverConnected = false;
    private boolean serverCameraActive = false;
    private int totalFramesReceived = 0;
    private int framesWithFaces = 0;
    private int framesSentToServer = 0;
    private int successfulRecognitions = 0;
    private long lastRecognitionTime = 0;
    private long lastFrameRequestTime = 0;
    private final int RECOGNITION_INTERVAL = 2000;
    private final int FRAME_REQUEST_INTERVAL = 500;

    private StatusManager statusManager;

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

        localFaceDetector = new LocalFaceDetector();
        requestQueue = Volley.newRequestQueue(this);
        executorService = Executors.newFixedThreadPool(3);
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

        @SuppressLint("DefaultLocale") JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        String status = response.getString("status");
                        if ("healthy".equals(status)) {
                            serverConnected = true;

                            int peopleCount = response.getInt("people_count");
                            boolean cameraActive = response.optBoolean("camera_active", false);

                            if (cameraActive) {
                                serverCameraActive = true;
                                statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,"Smart Glasses Connected",String.format("Camera active • %d people registered", peopleCount));
                                speak(String.format(StringResources.getString(FaceRecognition.SMART_GLASSES_CONNECTED), peopleCount));
                                updateInstructions("Smart glasses ready! Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
                            } else {
                                statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTING,
                                        "Server Connected",
                                        String.format("Starting camera • %d people registered", peopleCount));

                                speak(String.format(StringResources.getString(FaceRecognition.SERVER_CONNECTED), peopleCount));
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
                    handleServerError("Smart glasses server not found. Check if server is running on " + SERVER_URL);
                });

        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
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
                                    "Smart Glasses Ready", "Camera active • Ready for recognition");

                            speak(StringResources.getString(FaceRecognition.CAMERA_ACTIVATED));
                            updateInstructions("Smart glasses ready! Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
                        } else {
                            handleServerError("Failed to start smart glasses camera");
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing camera start response", e);
                        handleServerError("Camera activation error");
                    }
                },
                error -> {
                    Log.e(TAG, "Camera start failed", error);
                    handleServerError("Could not activate smart glasses camera");
                });

        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
        requestQueue.add(request);
    }
    private void handleServerError(String message) {
        serverConnected = false;
        serverCameraActive = false;
        statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                "Connection Failed", message);
        updateInstructions(message);
        speak(message);
    }

    private void startRecognition() {
         if (!serverConnected) {
            speak("Smart glasses server not connected. Please check connection.");
            return;
        }
         if (!serverCameraActive) {
            speak("starting smart glass camera....");
            startServerCamera();
            mainHandler.postDelayed(()->{
                if(serverCameraActive){
                    startRecognition();
                }else{
                    speak("Smart glasses camera not active. Please check connection.");
                }
            },3000);
            return;
        }

         if(isRecognizing){
             return;
         }

        isRecognizing = true;
        btnStartRecognition.setVisibility(View.GONE);
        btnStopRecognition.setVisibility(View.VISIBLE);
        statusIndicator.setImageResource(R.drawable.ic_visibility_on);

        statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                "Recognition Active", "Processing smart glasses feed...");
        updateResults("Analyzing smart glasses camera feed with AI...");
        updateInstructions("Recognition running. Say 'STOP' to end or 'ADD FRIEND' if you see someone new");
        speak("Face recognition started. Processing smart glasses camera feed.");

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
                    "Smart Glasses Ready", "Recognition stopped • Ready to start");

            updateStatus("Recognition Stopped");
            updateInstructions("Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
            speak("Face recognition stopped");

            stopVoiceListening();
            showPerformanceStats();
        }
    }

    private void startFrameProcessing() {
        executorService.execute(this::frameProcessingLoop);
    }

    private void frameProcessingLoop() {
        while (isRecognizing) {
            try {
                if (System.currentTimeMillis() - lastFrameRequestTime > FRAME_REQUEST_INTERVAL) {
                    requestFrameFromServer();
                    lastFrameRequestTime = System.currentTimeMillis();
                }
                Thread.sleep(100);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    private void requestFrameFromServer() {

        if (!serverCameraActive) {
            Log.w(TAG, "Server camera not active, skipping frame request");
            return;
        }

        String url = SERVER_URL + "/api/camera/frame";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        totalFramesReceived++;

                        if(response.has("error")){
                            String errorMsg = response.getString("error");
                            Log.w(TAG, "Error requesting frame from server: " + errorMsg);
                            statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                                    "Frame Error", errorMsg);
                            mainHandler.post(() -> {
                                updateResults("⚠️ " + errorMsg);
                            });
                            return;
                        }

                        if (serverConnected && serverCameraActive && isRecognizing) {
                            statusManager.updateStatus(StatusManager.ConnectionStatus.CONNECTED,
                                    "Recognition Active", "Processing frames...");
                        }

                        String imageBase64 = response.getString("image");
                        boolean serverRecognized = response.optBoolean("recognized", false);
                        String serverMessage = response.optString("message", "Processing...");
                        double serverConfidence = response.optDouble("confidence", 0.0);
                        String recognizedName = response.optString("name", null);
                        String confidenceLevel = response.optString("confidence_level", "unknown");
                        Double qualityScore = response.optDouble("quality_score",0.0);
                        Double processingTime = response.optDouble("processing_time",0.0);
                        String methodUsed = response.optString("method_used", "unknown");

                        displayFrame(imageBase64);

                        processServerRecognitionResult(serverRecognized, recognizedName, serverMessage,
                                serverConfidence, confidenceLevel, qualityScore,
                                processingTime, methodUsed);

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing frame response", e);
                    }
                },
                error -> {
                    Log.e(TAG, "Frame request error", error);
                    statusManager.updateStatus(StatusManager.ConnectionStatus.ERROR,
                            "Connection Issue", "Smart glasses feed interrupted");
                    if (isRecognizing) {
                        mainHandler.post(() -> {
                            updateResults("⚠️ Connection to smart glasses interrupted");
                        });
                    }
                });

        request.setRetryPolicy(new DefaultRetryPolicy(3000, 0, 0));
        requestQueue.add(request);
    }

    private void displayFrame(String imageBase64) {
        try {
            byte[] imageBytes = Base64.decode(imageBase64, Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);
            File f = new File(getExternalFilesDir(null), "last_frame.jpg");
            try (FileOutputStream fos = new FileOutputStream(f)) {
                fos.write(Base64.decode(imageBase64, Base64.DEFAULT));
            }
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

    private void processServerRecognitionResult(boolean recognized, String name, String message,
                                                double confidence, String confidenceLevel,
                                                double qualityScore, double processingTime,
                                                String methodUsed) {
        String resultMessage;
        if(recognized && name != null){
            framesWithFaces++;
            successfulRecognitions++;

            resultMessage = String.format("✅ Smart Glasses AI: %s\n" +
                            "🎯 Confidence: %.1f%% (%s)\n" +
                            "📊 Quality: %.1f%%\n" +
                            "⚡ Processing: %.0fms\n" +
                            "🔧 Method: %s",
                    name,
                    confidence * 100,
                    confidenceLevel,
                    qualityScore * 100,
                    processingTime * 1000,
                    methodUsed);

            if (System.currentTimeMillis() - lastRecognitionTime > RECOGNITION_INTERVAL) {
                speak(name + " identified");
                lastRecognitionTime = System.currentTimeMillis();
            }
        } else if(qualityScore > 0.3){
            framesWithFaces++;

            resultMessage = String.format("❓ Smart Glasses AI: %s\n" +
                            "🎯 Similarity: %.1f%%\n" +
                            "📊 Quality: %.1f%%\n" +
                            "⚡ Processing: %.0fms",
                    message,
                    confidence * 100,
                    qualityScore * 100,
                    processingTime * 1000);
        } else {
            resultMessage = String.format("👀 Smart Glasses AI: %s\n" +
                            "⚡ Processing: %.0fms",
                    message,
                    processingTime * 1000);
        }

        mainHandler.post(() -> {
            updateResults(resultMessage);
            updatePerformanceDisplay();
        });

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
        } else if (lowerCommand.contains("add friend") || lowerCommand.contains("register") ||
                lowerCommand.contains("new face")) {
            speak("Opening face registration");
            startActivity(new Intent(this, AddFriendActivity.class));
        } else if (lowerCommand.contains("back") || lowerCommand.contains("return")) {
            speak("Going back to main menu");
            finish();
        } else if (lowerCommand.contains("stats") || lowerCommand.contains("performance")) {
            showPerformanceStats();
        } else if (isRecognizing) {
            speak("Commands available: stop, add friend, stats, or back");
        } else {
            speak("Commands available: start, add friend, or back");
        }
    }


    private void resetPerformanceStats() {
        totalFramesReceived = 0;
        framesWithFaces = 0;
        framesSentToServer = 0;
        successfulRecognitions = 0;
        lastRecognitionTime = 0;
        lastFrameRequestTime = 0;

        if (localFaceDetector != null) {
            localFaceDetector.resetStats();
        }
    }
    private void updatePerformanceDisplay() {
        if (performanceText == null) return;

        float faceDetectionRate = totalFramesReceived > 0 ?
                (float) framesWithFaces / totalFramesReceived * 100 : 0;

        float recognitionSuccessRate = framesWithFaces > 0 ?
                (float) successfulRecognitions / framesWithFaces * 100 : 0;

        String performance = String.format(
                "📊 Frames: %d | Faces: %d (%.1f%%) | Recognized: %d (%.1f%%)",
                totalFramesReceived, framesWithFaces, faceDetectionRate,
                successfulRecognitions, recognitionSuccessRate
        );

        performanceText.setText(performance);
    }

    private void showPerformanceStats() {
        LocalFaceDetector.DetectionStats stats = localFaceDetector.getStats();

        String statsMessage = String.format(
                "Performance Stats: Received %d frames from smart glasses, detected faces in %d frames (%.1f%% rate), " +
                        "%d successful recognitions (%.1f%% success rate). " +
                        "Average local processing time: %.1f milliseconds.",
                totalFramesReceived, framesWithFaces,
                totalFramesReceived > 0 ? (float) framesWithFaces / totalFramesReceived * 100 : 0,
                successfulRecognitions,
                framesWithFaces > 0 ? (float) successfulRecognitions / framesWithFaces * 100 : 0,
                stats.getAvgProcessingTime()
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
        speak(text, null);
    }

    private void speak(String text, Locale locale) {
        if (ttsEngine != null) {
            if (locale != null && locale != ttsEngine.getLanguage()) {
                ttsEngine.setLanguage(locale);
            }
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "SMART_GLASSES_UTTERANCE");
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
            int result = ttsEngine.setLanguage(Locale.US);
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                    result == TextToSpeech.LANG_NOT_SUPPORTED) {
                updateStatus("TTS Language not supported");
            } else {
                mainHandler.postDelayed(() -> {
                    if (!isRecognizing) {
                        startVoiceListening();
                    }
                }, 1000);
            }
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

        if (localFaceDetector != null) {
            localFaceDetector.release();
        }

        if (executorService != null) {
            executorService.shutdown();
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

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == AUDIO_PERMISSION_REQUEST) {
            boolean allPermissionsGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allPermissionsGranted = false;
                    break;
                }
            }

            if (allPermissionsGranted) {
                speak("Audio permission granted. Smart glasses interface ready.");
            } else {
                speak("Microphone permission is required for voice commands.");
                finish();
            }
        }
    }
}
