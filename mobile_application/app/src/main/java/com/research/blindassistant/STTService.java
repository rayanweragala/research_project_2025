package com.research.blindassistant;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import androidx.annotation.Nullable;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class STTService extends Service {
    private static final String TAG = "STTService";

    // Default Raspberry Pi IP - Change this to your Pi's IP address
    private static final String DEFAULT_PI_IP = "192.168.1.100";
    private static final String DEFAULT_PORT = "5002";
    private static final int CONNECTION_TIMEOUT = 10000; // 10 seconds
    private static final int READ_TIMEOUT = 30000; // 30 seconds

    private String piServerUrl;
    private ExecutorService executorService;
    private Handler mainHandler;
    private STTServiceBinder binder = new STTServiceBinder();

    // Interface for STT callbacks
    public interface STTCallback {
        void onTranscriptionSuccess(String transcription, TranscriptionInfo info);
        void onTranscriptionError(String error);
        void onServerHealthCheck(boolean isHealthy, ServerStatus status);
    }

    // Data classes for response information
    public static class TranscriptionInfo {
        public final double duration;
        public final int sampleRate;
        public final double processingTime;
        public final String timestamp;

        public TranscriptionInfo(double duration, int sampleRate, double processingTime, String timestamp) {
            this.duration = duration;
            this.sampleRate = sampleRate;
            this.processingTime = processingTime;
            this.timestamp = timestamp;
        }
    }

    public static class ServerStatus {
        public final boolean sttModelAvailable;
        public final boolean microphoneAvailable;
        public final String modelType;
        public final double uptime;
        public final int totalRequests;
        public final int successfulTranscriptions;
        public final double avgAccuracy;

        public ServerStatus(boolean sttModelAvailable, boolean microphoneAvailable,
                            String modelType, double uptime, int totalRequests,
                            int successfulTranscriptions, double avgAccuracy) {
            this.sttModelAvailable = sttModelAvailable;
            this.microphoneAvailable = microphoneAvailable;
            this.modelType = modelType;
            this.uptime = uptime;
            this.totalRequests = totalRequests;
            this.successfulTranscriptions = successfulTranscriptions;
            this.avgAccuracy = avgAccuracy;
        }
    }

    public class STTServiceBinder extends Binder {
        public STTService getService() {
            return STTService.this;
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "STTService created");

        executorService = Executors.newCachedThreadPool();
        mainHandler = new Handler(Looper.getMainLooper());

        // Initialize with default or saved server URL
        String savedIp = getSharedPreferences("stt_prefs", MODE_PRIVATE)
                .getString("pi_server_ip", DEFAULT_PI_IP);
        String savedPort = getSharedPreferences("stt_prefs", MODE_PRIVATE)
                .getString("pi_server_port", DEFAULT_PORT);

        setServerUrl(savedIp, savedPort);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "STTService destroyed");

        if (executorService != null) {
            executorService.shutdown();
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return binder;
    }

    /**
     * Set the Raspberry Pi server URL
     */
    public void setServerUrl(String ipAddress, String port) {
        this.piServerUrl = "http://" + ipAddress + ":" + port;

        // Save to preferences
        getSharedPreferences("stt_prefs", MODE_PRIVATE)
                .edit()
                .putString("pi_server_ip", ipAddress)
                .putString("pi_server_port", port)
                .apply();

        Log.d(TAG, "Server URL set to: " + piServerUrl);
    }

    /**
     * Get current server URL
     */
    public String getServerUrl() {
        return piServerUrl;
    }

    /**
     * Check if STT server is healthy
     */
    public void checkServerHealth(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/health");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Accept", "application/json");

                int responseCode = connection.getResponseCode();

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    String response = readResponse(connection);
                    JSONObject jsonResponse = new JSONObject(response);

                    boolean isHealthy = "healthy".equals(jsonResponse.optString("status"));
                    boolean sttModelAvailable = jsonResponse.optBoolean("stt_model_available", false);
                    boolean microphoneAvailable = jsonResponse.optBoolean("microphone_available", false);
                    String modelType = jsonResponse.optString("stt_model_type", "unknown");
                    double uptime = jsonResponse.optDouble("uptime_seconds", 0);

                    JSONObject stats = jsonResponse.optJSONObject("stats");
                    int totalRequests = 0;
                    int successfulTranscriptions = 0;
                    if (stats != null) {
                        totalRequests = stats.optInt("total_requests", 0);
                        successfulTranscriptions = stats.optInt("successful_transcriptions", 0);
                    }

                    double avgAccuracy = jsonResponse.optDouble("avg_accuracy", 0);

                    ServerStatus status = new ServerStatus(sttModelAvailable, microphoneAvailable,
                            modelType, uptime, totalRequests, successfulTranscriptions, avgAccuracy);

                    mainHandler.post(() -> callback.onServerHealthCheck(isHealthy, status));
                } else {
                    String error = "Server returned code: " + responseCode;
                    mainHandler.post(() -> callback.onServerHealthCheck(false, null));
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Health check failed", e);
                mainHandler.post(() -> callback.onServerHealthCheck(false, null));
            }
        });
    }

    /**
     * Transcribe audio file by sending file path to server
     */
    public void transcribeAudioFile(String filePath, STTCallback callback) {
        if (filePath == null || filePath.trim().isEmpty()) {
            mainHandler.post(() -> callback.onTranscriptionError("File path is empty"));
            return;
        }

        File audioFile = new File(filePath);
        if (!audioFile.exists()) {
            mainHandler.post(() -> callback.onTranscriptionError("Audio file does not exist: " + filePath));
            return;
        }

        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/transcribe_path");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setRequestProperty("Accept", "application/json");
                connection.setDoOutput(true);

                // Create JSON payload
                JSONObject payload = new JSONObject();
                payload.put("file_path", filePath);

                // Send request
                try (OutputStream os = connection.getOutputStream()) {
                    byte[] input = payload.toString().getBytes(StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }

                int responseCode = connection.getResponseCode();
                String response = readResponse(connection);

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    parseTranscriptionResponse(response, callback);
                } else {
                    handleErrorResponse(response, callback, "Transcription failed with code: " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Transcription failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Network error: " + e.getMessage()));
            }
        });
    }

    /**
     * Start recording on the server
     */
    public void startServerRecording(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/start_recording");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Accept", "application/json");

                int responseCode = connection.getResponseCode();
                String response = readResponse(connection);

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    JSONObject jsonResponse = new JSONObject(response);
                    boolean success = jsonResponse.optBoolean("success", false);

                    if (success) {
                        mainHandler.post(() -> callback.onTranscriptionSuccess("Recording started", null));
                    } else {
                        String error = jsonResponse.optString("error", "Unknown error starting recording");
                        mainHandler.post(() -> callback.onTranscriptionError(error));
                    }
                } else {
                    handleErrorResponse(response, callback, "Failed to start recording: " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Start recording failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Network error: " + e.getMessage()));
            }
        });
    }

    /**
     * Stop recording on server and get transcription
     */
    public void stopServerRecording(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/stop_recording");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Accept", "application/json");

                int responseCode = connection.getResponseCode();
                String response = readResponse(connection);

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    parseTranscriptionResponse(response, callback);
                } else {
                    handleErrorResponse(response, callback, "Failed to stop recording: " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Stop recording failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Network error: " + e.getMessage()));
            }
        });
    }

    /**
     * Cancel ongoing recording on server
     */
    public void cancelServerRecording(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/cancel_recording");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Accept", "application/json");

                int responseCode = connection.getResponseCode();
                String response = readResponse(connection);

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    JSONObject jsonResponse = new JSONObject(response);
                    boolean success = jsonResponse.optBoolean("success", false);

                    if (success) {
                        mainHandler.post(() -> callback.onTranscriptionSuccess("Recording cancelled", null));
                    } else {
                        String error = jsonResponse.optString("error", "Unknown error cancelling recording");
                        mainHandler.post(() -> callback.onTranscriptionError(error));
                    }
                } else {
                    handleErrorResponse(response, callback, "Failed to cancel recording: " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Cancel recording failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Network error: " + e.getMessage()));
            }
        });
    }

    /**
     * Get recording status from server
     */
    public void getRecordingStatus(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/recording_status");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(CONNECTION_TIMEOUT);
                connection.setReadTimeout(READ_TIMEOUT);
                connection.setRequestProperty("Accept", "application/json");

                int responseCode = connection.getResponseCode();
                String response = readResponse(connection);

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    JSONObject jsonResponse = new JSONObject(response);
                    JSONObject status = jsonResponse.optJSONObject("status");

                    if (status != null) {
                        boolean isRecording = status.optBoolean("is_recording", false);
                        String statusMessage = isRecording ? "Recording in progress" : "Not recording";
                        mainHandler.post(() -> callback.onTranscriptionSuccess(statusMessage, null));
                    } else {
                        mainHandler.post(() -> callback.onTranscriptionError("Invalid status response"));
                    }
                } else {
                    handleErrorResponse(response, callback, "Failed to get status: " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Get status failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Network error: " + e.getMessage()));
            }
        });
    }

    /**
     * Parse transcription response and extract information
     */
    private void parseTranscriptionResponse(String response, STTCallback callback) {
        try {
            JSONObject jsonResponse = new JSONObject(response);
            boolean success = jsonResponse.optBoolean("success", false);

            if (success) {
                String transcription = jsonResponse.optString("transcription", "");

                // Extract audio info
                JSONObject audioInfo = jsonResponse.optJSONObject("audio_info");
                double duration = 0;
                int sampleRate = 0;
                if (audioInfo != null) {
                    duration = audioInfo.optDouble("duration", 0);
                    sampleRate = audioInfo.optInt("sample_rate", 0);
                }

                double processingTime = jsonResponse.optDouble("processing_time", 0);
                String timestamp = String.valueOf(jsonResponse.optLong("timestamp", System.currentTimeMillis()));

                TranscriptionInfo info = new TranscriptionInfo(duration, sampleRate, processingTime, timestamp);

                mainHandler.post(() -> callback.onTranscriptionSuccess(transcription, info));
            } else {
                String error = jsonResponse.optString("error", "Unknown transcription error");
                mainHandler.post(() -> callback.onTranscriptionError(error));
            }
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing transcription response", e);
            mainHandler.post(() -> callback.onTranscriptionError("Response parsing error: " + e.getMessage()));
        }
    }

    /**
     * Handle error responses from server
     */
    private void handleErrorResponse(String response, STTCallback callback, String defaultError) {
        try {
            JSONObject jsonResponse = new JSONObject(response);
            String error = jsonResponse.optString("error", defaultError);
            mainHandler.post(() -> callback.onTranscriptionError(error));
        } catch (JSONException e) {
            mainHandler.post(() -> callback.onTranscriptionError(defaultError));
        }
    }

    /**
     * Read HTTP response
     */
    private String readResponse(HttpURLConnection connection) throws IOException {
        StringBuilder response = new StringBuilder();

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(
                        connection.getResponseCode() >= 400 ?
                                connection.getErrorStream() : connection.getInputStream()
                )
        )) {
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
        }

        return response.toString();
    }

    /**
     * Test network connectivity to server
     */
    public void testConnection(STTCallback callback) {
        executorService.execute(() -> {
            try {
                URL url = new URL(piServerUrl + "/stt/health");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000); // Shorter timeout for test
                connection.setReadTimeout(5000);

                int responseCode = connection.getResponseCode();
                connection.disconnect();

                if (responseCode == HttpURLConnection.HTTP_OK) {
                    mainHandler.post(() -> callback.onTranscriptionSuccess("Connection successful", null));
                } else {
                    mainHandler.post(() -> callback.onTranscriptionError("Server responded with code: " + responseCode));
                }

            } catch (Exception e) {
                Log.e(TAG, "Connection test failed", e);
                mainHandler.post(() -> callback.onTranscriptionError("Connection failed: " + e.getMessage()));
            }
        });
    }
}