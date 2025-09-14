package com.research.blindassistant;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.Locale;

public class DistanceSensorService {

    private static final String TAG = "DistanceSensorService";
    private static final String SERVER_URL = "http://10.72.250.126:5001";
    private static final double OBSTACLE_THRESHOLD = 15.0; // 15cm threshold
    private static final String SINHALA_WARNING = "නවතන්න ඉදිරියෙන් බාධකයක්"; // "Stop, obstacle ahead"
    private static final int MONITORING_INTERVAL = 4000; // 4 seconds to match server

    private RequestQueue requestQueue;
    private Handler monitoringHandler;
    private Runnable monitoringRunnable;
    private TextToSpeech textToSpeech;
    private DistanceSensorCallback callback;
    private boolean isMonitoring = false;
    private boolean isTtsReady = false;
    private long lastWarningTime = 0;
    private static final long WARNING_COOLDOWN = 3000; // 3 seconds cooldown between warnings

    public interface DistanceSensorCallback {
        void onDistanceMeasured(double distance, String zone);
        void onObstacleDetected(double distance);
        void onServerStarted(boolean success, String message);
        void onConnectionError(String error);
    }

    public DistanceSensorService(Context context) {
        requestQueue = Volley.newRequestQueue(context);
        monitoringHandler = new Handler(Looper.getMainLooper());

        // Initialize Text-to-Speech
        initTextToSpeech(context);

        // Auto-start the server and monitoring
        autoStartService();
    }

    public void setCallback(DistanceSensorCallback callback) {
        this.callback = callback;
    }

    private void initTextToSpeech(Context context) {
        textToSpeech = new TextToSpeech(context, status -> {
            if (status == TextToSpeech.SUCCESS) {
                // Set language to Sinhala
                int result = textToSpeech.setLanguage(new Locale("si", "LK"));
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.w(TAG, "Sinhala language not supported, using default language");
                    textToSpeech.setLanguage(Locale.getDefault());
                }
                isTtsReady = true;
                Log.d(TAG, "Text-to-Speech initialized successfully");
            } else {
                Log.e(TAG, "Text-to-Speech initialization failed");
            }
        });
    }

    private void autoStartService() {
        Log.d(TAG, "Auto-starting distance sensor service...");

        // First check server health
        checkServerHealth();

        // Start the sensor after a brief delay
        monitoringHandler.postDelayed(() -> {
            startSensor();
        }, 1000);

        // Start monitoring after sensor initialization
        monitoringHandler.postDelayed(() -> {
            startContinuousMonitoring();
        }, 3000);
    }

    private void checkServerHealth() {
        String url = SERVER_URL + "/api/health";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        boolean healthy = "healthy".equals(response.getString("status"));
                        Log.d(TAG, "Server health check: " + (healthy ? "Healthy" : "Not healthy"));
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing health response", e);
                    }
                },
                error -> {
                    Log.w(TAG, "Server health check failed - server may be starting");
                }
        );

        requestQueue.add(request);
    }

    private void startSensor() {
        String url = SERVER_URL + "/api/sensor/start";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.POST, url, null,
                response -> {
                    try {
                        boolean success = response.getBoolean("success");
                        String message = response.getString("message");

                        Log.d(TAG, "Sensor start result: " + message);

                        if (callback != null) {
                            callback.onServerStarted(success, message);
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing start response", e);
                        if (callback != null) {
                            callback.onServerStarted(false, "Response parsing error");
                        }
                    }
                },
                error -> {
                    Log.e(TAG, "Sensor start request failed", error);
                    if (callback != null) {
                        callback.onServerStarted(false, "Sensor start request failed");
                    }
                }
        );

        requestQueue.add(request);
    }

    public void startContinuousMonitoring() {
        if (isMonitoring) {
            Log.d(TAG, "Monitoring already active");
            return;
        }

        isMonitoring = true;
        Log.d(TAG, "Starting continuous distance monitoring...");

        monitoringRunnable = new Runnable() {
            @Override
            public void run() {
                if (isMonitoring) {
                    getCurrentDistance();
                    monitoringHandler.postDelayed(this, MONITORING_INTERVAL);
                }
            }
        };

        monitoringHandler.post(monitoringRunnable);
    }

    public void stopContinuousMonitoring() {
        isMonitoring = false;
        if (monitoringRunnable != null) {
            monitoringHandler.removeCallbacks(monitoringRunnable);
        }
        Log.d(TAG, "Stopped continuous monitoring");
    }

    private void getCurrentDistance() {
        String url = SERVER_URL + "/api/distance/current";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        double distance = response.getDouble("distance");
                        String zone = response.getString("zone");

                        Log.d(TAG, String.format("Distance: %.2f cm, Zone: %s", distance, zone));

                        if (callback != null) {
                            callback.onDistanceMeasured(distance, zone);
                        }

                        // Check for obstacle detection
                        checkObstacle(distance);

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing distance response", e);
                        if (callback != null) {
                            callback.onConnectionError("Distance response parsing error");
                        }
                    }
                },
                error -> {
                    Log.e(TAG, "Current distance request failed", error);
                    if (callback != null) {
                        callback.onConnectionError("Distance request failed");
                    }
                }
        );

        requestQueue.add(request);
    }

    private void checkObstacle(double distance) {
        if (distance <= OBSTACLE_THRESHOLD) {
            long currentTime = System.currentTimeMillis();

            // Implement cooldown to prevent spam warnings
            if (currentTime - lastWarningTime > WARNING_COOLDOWN) {
                Log.w(TAG, String.format("OBSTACLE DETECTED! Distance: %.2f cm", distance));

                // Trigger callback
                if (callback != null) {
                    callback.onObstacleDetected(distance);
                }

                // Speak warning in Sinhala
                speakWarning();

                lastWarningTime = currentTime;
            }
        }
    }

    private void speakWarning() {
        if (isTtsReady && textToSpeech != null) {
            Log.d(TAG, "Speaking warning: " + SINHALA_WARNING);
            textToSpeech.speak(SINHALA_WARNING, TextToSpeech.QUEUE_FLUSH, null, "obstacle_warning");
        } else {
            Log.w(TAG, "TTS not ready, cannot speak warning");
        }
    }

    public void setObstacleThreshold(double threshold) {
        // Allow dynamic threshold adjustment if needed
        Log.d(TAG, "Obstacle threshold would be set to: " + threshold + " cm (currently fixed at 15cm)");
    }

    public boolean isMonitoringActive() {
        return isMonitoring;
    }

    public void restart() {
        Log.d(TAG, "Restarting distance sensor service...");
        stopContinuousMonitoring();

        // Restart after brief delay
        monitoringHandler.postDelayed(() -> {
            autoStartService();
        }, 2000);
    }

    public void cleanup() {
        Log.d(TAG, "Cleaning up distance sensor service...");

        stopContinuousMonitoring();

        if (requestQueue != null) {
            requestQueue.cancelAll(TAG);
        }

        if (textToSpeech != null) {
            textToSpeech.stop();
            textToSpeech.shutdown();
        }

        if (monitoringHandler != null) {
            monitoringHandler.removeCallbacksAndMessages(null);
        }
    }
}