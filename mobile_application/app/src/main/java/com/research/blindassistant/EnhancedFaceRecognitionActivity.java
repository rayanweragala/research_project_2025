package com.research.blindassistant;

import android.Manifest;
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
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_enhanced_face_recognition_server);

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

        speak("Smart glasses interface ready. Connecting to camera server.");
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

        updateConnectionStatus();
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
            speak("Going back to main menu");
            finish();
        });
        btnAddFriend.setOnClickListener(v -> {
            speak("Opening face registration");
            startActivity(new Intent(this, AddFriendActivity.class));
        });
    }
    private void addHapticFeedback() {
        View[] buttons = {btnStartRecognition, btnStopRecognition, btnBack, btnAddFriend};

        for (View button : buttons) {
            button.setOnLongClickListener(v -> {
                v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS);
                String buttonText = ((Button) v).getText().toString();
                speak("Button: " + buttonText);
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

                            updateConnectionStatus();

                            if (cameraActive) {
                                serverCameraActive = true;
                                speak(String.format("Smart glasses connected. Camera active. %d people registered.", peopleCount));
                                updateInstructions("Smart glasses ready! Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
                            } else {
                                speak(String.format("Server connected with %d people registered. Starting camera...", peopleCount));
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
                            updateConnectionStatus();
                            speak("Smart glasses camera activated");
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
        updateConnectionStatus();
        updateInstructions(message);
        speak(message);
    }

    private void startRecognition() {
        if (!isRecognizing && serverConnected && serverCameraActive) {
            isRecognizing = true;
            btnStartRecognition.setVisibility(View.GONE);
            btnStopRecognition.setVisibility(View.VISIBLE);
            statusIndicator.setImageResource(R.drawable.ic_visibility_on);

            updateStatus("Recognition Active - Receiving Smart Glasses Feed");
            updateResults("Analyzing smart glasses camera feed with AI...");
            updateInstructions("Recognition running. Say 'STOP' to end or 'ADD FRIEND' if you see someone new");
            speak("Face recognition started. Processing smart glasses camera feed.");

            startVoiceListening();
            resetPerformanceStats();
            startFrameProcessing();

        } else if (!serverConnected) {
            speak("Smart glasses server not connected. Please check connection.");
        } else if (!serverCameraActive) {
            speak("Smart glasses camera not active. Please wait for camera initialization.");
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
        String url = SERVER_URL + "/api/camera/frame";

        JsonObjectRequest request = new JsonObjectRequest(Request.Method.GET, url, null,
                response -> {
                    try {
                        totalFramesReceived++;

                        String imageBase64 = response.getString("image");
                        boolean serverRecognized = response.optBoolean("recognized", false);
                        String serverMessage = response.optString("message", "Processing...");
                        double serverConfidence = response.optDouble("confidence", 0.0);

                        displayFrame(imageBase64);

                        processFrameLocally(imageBase64, serverRecognized, serverMessage, serverConfidence);

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing frame response", e);
                    }
                },
                error -> {
                    Log.e(TAG, "Frame request error", error);
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

            if (bitmap != null) {
                mainHandler.post(() -> {
                    cameraFeedView.setImageBitmap(bitmap);
                });
            }
        } catch (Exception e) {
            Log.e(TAG, "Error displaying frame", e);
        }
    }

    private void processFrameLocally(String imageBase64, boolean serverRecognized,
                                     String serverMessage, double serverConfidence) {
        try {
            byte[] imageBytes = Base64.decode(imageBase64, Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);

            if (bitmap == null) return;

            LocalFaceDetector.FaceDetectionResult localResult = localFaceDetector.detectFaces(bitmap);

            if (localResult.hasFaces()) {
                framesWithFaces++;

                String resultMessage;
                if (serverRecognized) {
                    successfulRecognitions++;
                    resultMessage = String.format("✅ Smart Glasses: %s (%.1f%% confidence)",
                            serverMessage, serverConfidence * 100);

                    if (System.currentTimeMillis() - lastRecognitionTime > RECOGNITION_INTERVAL) {
                        speak(serverMessage.replace("Recognized ", "") + " identified");
                        lastRecognitionTime = System.currentTimeMillis();
                    }
                } else {
                    resultMessage = String.format("❓ Smart Glasses: %s (%.1f%% similarity)",
                            serverMessage, serverConfidence * 100);
                }

                resultMessage += String.format("\n🔍 Local AI: %s (Quality: %.1f%%)",
                        localResult.getMessage(), localResult.getQualityScore() * 100);

                final String finalMessage = resultMessage;
                mainHandler.post(() -> {
                    updateResults(finalMessage);
                    updatePerformanceDisplay();
                });
            } else {
                if (serverRecognized || serverConfidence > 0.3) {
                    String resultMessage = String.format("📱 Smart Glasses: %s (%.1f%%)",
                            serverMessage, serverConfidence * 100);

                    mainHandler.post(() -> {
                        updateResults(resultMessage);
                        updatePerformanceDisplay();
                    });
                }
            }

        } catch (Exception e) {
            Log.e(TAG, "Error processing frame locally", e);
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

    private void processFrame(byte[] data, Camera camera) {
        try {
            Camera.Size previewSize = camera.getParameters().getPreviewSize();
            YuvImage yuvImage = new YuvImage(data, ImageFormat.NV21,
                    previewSize.width, previewSize.height, null);

            ByteArrayOutputStream out = new ByteArrayOutputStream();
            yuvImage.compressToJpeg(new Rect(0, 0, previewSize.width, previewSize.height), 70, out);
            byte[] imageBytes = out.toByteArray();
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);

            if (bitmap == null) return;

            LocalFaceDetector.FaceDetectionResult faceResult = localFaceDetector.detectFaces(bitmap);

            if (faceResult.hasFaces()) {
                framesWithFaces++;

                if (faceResult.getQualityScore() > 0.5f &&
                        System.currentTimeMillis() - lastRecognitionTime > RECOGNITION_INTERVAL) {

                    sendFrameToServer(bitmap, faceResult);
                    lastRecognitionTime = System.currentTimeMillis();
                }

                mainHandler.post(() -> {
                    updateResults("Local AI: " + faceResult.getMessage() +
                            String.format(" (Quality: %.1f%%)", faceResult.getQualityScore() * 100));
                    updatePerformanceDisplay();
                });
            }

        } catch (Exception e) {
            Log.e(TAG, "Error processing frame", e);
        }
    }

    private void sendFrameToServer(Bitmap bitmap, LocalFaceDetector.FaceDetectionResult faceResult) {
        try {
            framesSentToServer++;

            ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.JPEG, 80, byteArrayOutputStream);
            byte[] byteArray = byteArrayOutputStream.toByteArray();
            String encoded = Base64.encodeToString(byteArray, Base64.DEFAULT);

            JSONObject jsonBody = new JSONObject();
            jsonBody.put("image", encoded);

            String url = SERVER_URL + "/api/recognize_realtime";

            JsonObjectRequest request = new JsonObjectRequest(Request.Method.POST, url, jsonBody,
                    response -> handleServerRecognitionResponse(response, faceResult),
                    error -> handleServerRecognitionError(error, faceResult));

            request.setRetryPolicy(new DefaultRetryPolicy(10000, 0, 0));
            requestQueue.add(request);

        } catch (Exception e) {
            Log.e(TAG, "Error sending frame to server", e);
        }
    }

    private void handleServerRecognitionResponse(JSONObject response, LocalFaceDetector.FaceDetectionResult localResult) {
        try {
            boolean recognized = response.getBoolean("recognized");
            String message = response.getString("message");
            double confidence = response.getDouble("confidence");
            double processingTime = response.getDouble("processing_time");

            if (recognized) {
                successfulRecognitions++;
                String name = response.getString("name");
                String result = String.format("✅ Server: %s (%.1f%% confidence)", name, confidence * 100);

                mainHandler.post(() -> {
                    updateResults(result);
                    updatePerformanceDisplay();
                });

                speak(String.format("%s identified", name));

            } else {
                String result = String.format("❓ Server: %s (%.1f%% similarity)", message, confidence * 100);

                mainHandler.post(() -> {
                    updateResults(result);
                    updatePerformanceDisplay();
                });
            }

            Log.d(TAG, String.format("Server processing time: %.0fms", processingTime * 1000));

        } catch (JSONException e) {
            Log.e(TAG, "Error parsing server response", e);
            handleServerRecognitionError(null, localResult);
        }
    }

    private void handleServerRecognitionError(VolleyError error, LocalFaceDetector.FaceDetectionResult localResult) {
        Log.e(TAG, "Server recognition error", error);

        mainHandler.post(() -> {
            updateResults("⚠️ Server error - using local detection: " + localResult.getMessage());
            updatePerformanceDisplay();
        });
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

    private void updateConnectionStatus() {
        if (serverConnected && serverCameraActive) {
            statusIndicator.setImageResource(R.drawable.ic_check_circle);
            statusIndicator.setContentDescription("Smart glasses connected and camera active");
        } else if (serverConnected) {
            statusIndicator.setImageResource(R.drawable.ic_warning);
            statusIndicator.setContentDescription("Server connected, camera starting");
        } else {
            statusIndicator.setImageResource(R.drawable.ic_error);
            statusIndicator.setContentDescription("Smart glasses server not connected");
        }
    }

    private void speak(String text) {
        if (ttsEngine != null) {
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
