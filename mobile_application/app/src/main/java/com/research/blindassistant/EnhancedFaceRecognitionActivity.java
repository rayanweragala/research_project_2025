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
import android.view.SurfaceHolder;
import android.view.SurfaceView;
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
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class EnhancedFaceRecognitionActivity extends AppCompatActivity
        implements TextToSpeech.OnInitListener, RecognitionListener, SurfaceHolder.Callback, Camera.PreviewCallback {

    private static final String TAG = "EnhancedFaceRecognition";
    private static final int CAMERA_PERMISSION_REQUEST = 100;
    private static final String SERVER_URL = "http://10.187.202.95:5000";

    private TextView statusText, resultsText, instructionsText, performanceText;
    private Button btnStartRecognition, btnStopRecognition, btnBack, btnAddFriend;
    private ImageView statusIndicator;
    private SurfaceView cameraPreview;
    private SurfaceHolder surfaceHolder;

    private TextToSpeech ttsEngine;
    private SpeechRecognizer speechRecognizer;
    private Intent speechRecognizerIntent;
    private Camera camera;
    private LocalFaceDetector localFaceDetector;
    private RequestQueue requestQueue;
    private ExecutorService executorService;
    private Handler mainHandler;

    private boolean isRecognizing = false;
    private boolean isListening = false;
    private boolean cameraInitialized = false;
    private boolean serverConnected = false;

    private int totalFramesProcessed = 0;
    private int framesWithFaces = 0;
    private int framesSentToServer = 0;
    private int successfulRecognitions = 0;
    private long lastRecognitionTime = 0;
    private final int RECOGNITION_INTERVAL = 2000;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_enhanced_face_recognition);

        initializeComponents();
        checkPermissions();
        setupVoiceRecognition();
        setupButtons();
        addHapticFeedback();

        localFaceDetector = new LocalFaceDetector();
        requestQueue = Volley.newRequestQueue(this);
        executorService = Executors.newFixedThreadPool(2);
        mainHandler = new Handler(Looper.getMainLooper());

        testServerConnection();

        speak("Enhanced face recognition ready. Checking camera and server connection.");
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
        cameraPreview = findViewById(R.id.cameraPreview);

        surfaceHolder = cameraPreview.getHolder();
        surfaceHolder.addCallback(this);

        updateConnectionStatus();
        updateInstructions("Initializing camera and server connection...");

        ttsEngine = new TextToSpeech(this, this);
    }

    private void checkPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO},
                    CAMERA_PERMISSION_REQUEST);
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
                            updateConnectionStatus();
                            speak(String.format("Server connected. %d people registered.", peopleCount));
                            updateInstructions("Say 'START' to begin recognition or 'ADD FRIEND' to register new faces");
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing server response", e);
                        handleServerError("Invalid server response");
                    }
                },
                error -> {
                    Log.e(TAG, "Server connection failed", error);
                    handleServerError("Server connection failed. Check if server is running on " + SERVER_URL);
                });

        request.setRetryPolicy(new DefaultRetryPolicy(5000, 1, 1.0f));
        requestQueue.add(request);
    }

    private void handleServerError(String message) {
        serverConnected = false;
        updateConnectionStatus();
        updateInstructions(message);
        speak(message);
    }

    private void startRecognition() {
        if (!isRecognizing && cameraInitialized && serverConnected) {
            isRecognizing = true;
            btnStartRecognition.setVisibility(View.GONE);
            btnStopRecognition.setVisibility(View.VISIBLE);
            statusIndicator.setImageResource(R.drawable.ic_visibility_on);

            updateStatus("Recognition Active - Processing Camera Feed");
            updateResults("Analyzing camera feed with local face detection...");
            updateInstructions("Recognition running. Say 'STOP' to end or 'ADD FRIEND' if you see someone new");
            speak("Face recognition started. Using local AI to filter frames and server for identification.");

            startVoiceListening();
            resetPerformanceStats();

        } else if (!cameraInitialized) {
            speak("Camera not ready. Please wait for camera initialization.");
        } else if (!serverConnected) {
            speak("Server not connected. Please check server connection.");
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

    @Override
    public void onPreviewFrame(byte[] data, Camera camera) {
        if (!isRecognizing) return;

        totalFramesProcessed++;

        executorService.execute(() -> processFrame(data, camera));
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
        totalFramesProcessed = 0;
        framesWithFaces = 0;
        framesSentToServer = 0;
        successfulRecognitions = 0;
        lastRecognitionTime = 0;

        if (localFaceDetector != null) {
            localFaceDetector.resetStats();
        }
    }

    private void updatePerformanceDisplay() {
        if (performanceText == null) return;

        float faceDetectionRate = totalFramesProcessed > 0 ?
                (float) framesWithFaces / totalFramesProcessed * 100 : 0;

        float serverSuccessRate = framesSentToServer > 0 ?
                (float) successfulRecognitions / framesSentToServer * 100 : 0;

        String performance = String.format(
                "📊 Frames: %d | Faces: %d (%.1f%%) | Server: %d | Success: %d (%.1f%%)",
                totalFramesProcessed, framesWithFaces, faceDetectionRate,
                framesSentToServer, successfulRecognitions, serverSuccessRate
        );

        performanceText.setText(performance);
    }

    private void showPerformanceStats() {
        LocalFaceDetector.DetectionStats stats = localFaceDetector.getStats();

        String statsMessage = String.format(
                "Performance Stats: Processed %d frames, detected faces in %d frames (%.1f%% rate), " +
                        "sent %d frames to server, %d successful recognitions. " +
                        "Average local processing time: %.1f milliseconds.",
                totalFramesProcessed, framesWithFaces,
                totalFramesProcessed > 0 ? (float) framesWithFaces / totalFramesProcessed * 100 : 0,
                framesSentToServer, successfulRecognitions,
                stats.getAvgProcessingTime()
        );

        speak(statsMessage);
        updateResults("📊 " + statsMessage);
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        try {
            camera = Camera.open();
            camera.setPreviewDisplay(holder);

            Camera.Parameters parameters = camera.getParameters();

            List<Camera.Size> previewSizes = parameters.getSupportedPreviewSizes();
            Camera.Size bestSize = previewSizes.get(0);
            for (Camera.Size size : previewSizes) {
                if (size.width <= 640 && size.height <= 480) {
                    bestSize = size;
                    break;
                }
            }

            parameters.setPreviewSize(bestSize.width, bestSize.height);
            parameters.setPreviewFormat(ImageFormat.NV21);
            camera.setParameters(parameters);

            camera.setPreviewCallback(this);
            camera.startPreview();

            cameraInitialized = true;
            updateConnectionStatus();

            Log.d(TAG, String.format("Camera initialized: %dx%d", bestSize.width, bestSize.height));

        } catch (IOException e) {
            Log.e(TAG, "Error setting camera preview", e);
            speak("Camera initialization failed");
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        if (camera != null) {
            camera.stopPreview();
            camera.setPreviewCallback(null);
            camera.release();
            camera = null;
            cameraInitialized = false;
        }
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
        if (cameraInitialized && serverConnected) {
            statusIndicator.setImageResource(R.drawable.ic_check_circle);
            statusIndicator.setContentDescription("Camera and server ready");
        } else if (cameraInitialized) {
            statusIndicator.setImageResource(R.drawable.ic_warning);
            statusIndicator.setContentDescription("Camera ready, server connecting");
        } else {
            statusIndicator.setImageResource(R.drawable.ic_error);
            statusIndicator.setContentDescription("Camera or server not ready");
        }
    }

    private void speak(String text) {
        if (ttsEngine != null) {
            ttsEngine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "BLIND_ASSISTANT_UTTERANCE");
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

        if (camera != null) {
            camera.release();
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

        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            boolean allPermissionsGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allPermissionsGranted = false;
                    break;
                }
            }

            if (allPermissionsGranted) {
                speak("Permissions granted. Initializing camera.");
            } else {
                speak("Camera and microphone permissions are required for face recognition.");
                finish();
            }
        }
    }
}
