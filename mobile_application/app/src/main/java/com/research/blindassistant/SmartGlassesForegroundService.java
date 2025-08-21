package com.research.blindassistant;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.android.volley.DefaultRetryPolicy;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;

import org.json.JSONException;
import android.os.Bundle;

import android.Manifest;
import android.content.pm.PackageManager;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import java.util.ArrayList;
import java.util.Locale;

public class SmartGlassesForegroundService extends Service implements TextToSpeech.OnInitListener {

    public static final String ACTION_START = "com.research.blindassistant.action.START";
    public static final String ACTION_STOP = "com.research.blindassistant.action.STOP";
    public static final String ACTION_CHECK_NOW = "com.research.blindassistant.action.CHECK_NOW";
    public static final String ACTION_START_CAMERA = "com.research.blindassistant.action.START_CAMERA";
    public static final String ACTION_STOP_CAMERA = "com.research.blindassistant.action.STOP_CAMERA";
    public static final String ACTION_COMPLETE_SHUTDOWN = "com.research.blindassistant.action.COMPLETE_SHUTDOWN";
    private static final String TAG = "SGForegroundService";
    private static final String CHANNEL_ID = "smart_glasses_monitor";
    private static final int NOTIF_ID = 1011;

    private static final String SERVER_URL = "http://10.231.176.126:5000";

    private Handler handler;
    private RequestQueue requestQueue;
    private boolean running;
    private boolean lastHealthy = false;
    private int peopleCount = 0;
    private long checkIntervalMs = 10_000;
    private boolean cameraWasActiveBeforeStop = false;
    private boolean cameraStoppedByAddFriend = false;

    private final Runnable periodicCheck = new Runnable() {
        @Override
        public void run() {
            if (!running) return;
            checkHealth(false);
            handler.postDelayed(this, checkIntervalMs);
        }
    };

    private TextToSpeech tts;
    private boolean ttsReady = false;
    private SpeechRecognizer speechRecognizer;
    private Intent speechIntent;
    private boolean isListening = false;
    private long lastTtsAtMs = 0L;
    private static final long TTS_THROTTLE_MS = 3000;
    private boolean isCompleteShutdown = false;

    @Override
    public void onCreate() {
        super.onCreate();
        handler = new Handler(Looper.getMainLooper());
        requestQueue = Volley.newRequestQueue(getApplicationContext());
        createChannel();
        startForeground(NOTIF_ID, buildNotification("Checking smart glasses status...", true));
        running = true;
        try {
            tts = new TextToSpeech(getApplicationContext(), this);
        } catch (Exception e) {
            Log.w(TAG, "TTS init failed", e);
        }

        setupBackgroundSpeechRecognizer();

        handler.post(periodicCheck);
        Log.d(TAG, "Foreground service created and started");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_STOP.equals(action)) {
                stopSelf();
                return START_NOT_STICKY;
            } else if (ACTION_COMPLETE_SHUTDOWN.equals(action)) {
                performCompleteShutdown();
                return START_NOT_STICKY;
            } else if (ACTION_CHECK_NOW.equals(action)) {
                checkHealth(true);
            } else if (ACTION_START_CAMERA.equals(action)) {
                startCamera();
            } else if (ACTION_STOP_CAMERA.equals(action)) {
                handleCameraStopRequest();
            }
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        running = false;
        handler.removeCallbacksAndMessages(null);

        if (requestQueue != null) requestQueue.stop();
        try {
            if (speechRecognizer != null) {
                speechRecognizer.destroy();
            }
        } catch (Exception ignored) {}
        try {
            if (tts != null) {
                tts.stop();
                tts.shutdown();
            }
        } catch (Exception ignored) {}

        Log.d(TAG, "Foreground service destroyed");
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) { return null; }

    private void performCompleteShutdown() {
        Log.d(TAG, "Performing complete shutdown of smart glasses system");
        isCompleteShutdown = true;
        running = false;

        String stopCameraUrl = SERVER_URL + "/api/camera/stop";
        JsonObjectRequest stopCameraRequest = new JsonObjectRequest(
                Request.Method.POST, stopCameraUrl, null,
                response -> {
                    Log.d(TAG, "Camera stopped successfully during shutdown");
                    stopSmartGlassesSystem();
                },
                error -> {
                    Log.w(TAG, "Failed to stop camera during shutdown, proceeding anyway", error);
                    stopSmartGlassesSystem();
                }
        );
        stopCameraRequest.setRetryPolicy(new DefaultRetryPolicy(3000, 0, 1f));
        requestQueue.add(stopCameraRequest);

        handler.postDelayed(() -> {
            if (isCompleteShutdown) {
                Log.d(TAG, "Forcing service shutdown due to timeout");
                stopSelf();
            }
        }, 5000);
    }

    private void stopSmartGlassesSystem() {
        String shutdownUrl = SERVER_URL + "/api/system/shutdown";
        JsonObjectRequest shutdownRequest = new JsonObjectRequest(
                Request.Method.POST, shutdownUrl, null,
                response -> {
                    Log.d(TAG, "Smart glasses system shutdown successfully");
                    finalizeShutdown();
                },
                error -> {
                    Log.w(TAG, "Failed to shutdown smart glasses system via API", error);
                    finalizeShutdown();
                }
        );
        shutdownRequest.setRetryPolicy(new DefaultRetryPolicy(3000, 0, 1f));
        requestQueue.add(shutdownRequest);
    }

    private void finalizeShutdown() {
        updateNotificationForShutdown();
        handler.postDelayed(() -> stopSelf(), 2000);
    }

    private void updateNotificationForShutdown() {
        String text = "Smart glasses system stopped completely";
        Notification shutdownNotification = buildShutdownNotification(text);
        getNotificationManager().notify(NOTIF_ID, shutdownNotification);
    }

    private Notification buildShutdownNotification(String contentText) {
        Intent openIntent = new Intent(this, MainActivity.class);
        PendingIntent contentPending = PendingIntent.getActivity(
                this, 0, openIntent,
                Build.VERSION.SDK_INT >= 31
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_stop)
                .setContentTitle("Blind Assistant")
                .setContentText(contentText)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(contentText))
                .setOngoing(false)
                .setAutoCancel(true)
                .setContentIntent(contentPending)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    private void checkHealth(boolean userInitiated) {
        String url = SERVER_URL + "/api/health";
        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        boolean healthy = "healthy".equals(response.getString("status"));
                        int count = response.optInt("people_count", 0);
                        boolean cameraActive = response.optBoolean("camera_active", false);

                        this.peopleCount = count;
                        if (cameraStoppedByAddFriend && !cameraActive && cameraWasActiveBeforeStop) {
                            Log.d(TAG, "Camera was stopped by AddFriend but should be active, attempting restart");
                            startCamera();
                            cameraStoppedByAddFriend = false;
                        }
                        updateState(healthy && cameraActive, count, userInitiated);
                    } catch (JSONException e) {
                        Log.e(TAG, "Parse error", e);
                        updateState(false, 0, userInitiated);
                    }
                },
                error -> {
                    Log.w(TAG, "Health check failed", error);
                    updateState(false, 0, userInitiated);
                }
        );
        request.setRetryPolicy(new DefaultRetryPolicy(4000, 0, 1f));
        requestQueue.add(request);
    }

    private void updateState(boolean healthyAndActive, int count, boolean announce) {
        String text;
        if (healthyAndActive) {
            text = "Smart glasses ready • Camera active • " + count + " people";
            if (!lastHealthy || announce) {
                notify(text, false);
                if (!cameraStoppedByAddFriend) {
                    speakThrottled("Smart glasses ready");
                }
            } else {
                getNotificationManager().notify(NOTIF_ID, buildNotification(text, false));
            }
        } else {
            if (cameraStoppedByAddFriend) {
                text = "Camera temporarily stopped for face registration";
            } else {
                text = "Smart glasses NOT active. Open app to reconnect.";
            }

            if (lastHealthy || announce) {
                notify(text, !cameraStoppedByAddFriend);
                if (!cameraStoppedByAddFriend) {
                    speakThrottled("Smart glasses not active");
                }
            } else {
                getNotificationManager().notify(NOTIF_ID, buildNotification(text, !cameraStoppedByAddFriend));
            }
        }
        lastHealthy = healthyAndActive;
    }

    private void handleCameraStopRequest() {
        Log.d(TAG, "Handling camera stop request from AddFriendActivity");

        String url = SERVER_URL + "/api/health";
        JsonObjectRequest healthRequest = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    boolean cameraActive = response.optBoolean("camera_active", false);
                    cameraWasActiveBeforeStop = cameraActive;

                    if (cameraActive) {
                        stopCameraForAddFriend();
                    } else {
                        Log.d(TAG, "Camera was already inactive");
                        cameraStoppedByAddFriend = true;
                    }
                },
                error -> {
                    Log.w(TAG, "Health check failed before stopping camera", error);
                    stopCameraForAddFriend();
                }
        );
        healthRequest.setRetryPolicy(new DefaultRetryPolicy(3000, 0, 1f));
        requestQueue.add(healthRequest);
    }

    private void stopCameraForAddFriend() {
        Log.d(TAG, "Stopping camera for AddFriendActivity");
        cameraStoppedByAddFriend = true;

        String url = SERVER_URL + "/api/camera/stop";
        JsonObjectRequest req = new JsonObjectRequest(Request.Method.POST, url, null,
                response -> {
                    Log.d(TAG, "Camera stopped successfully for AddFriendActivity");
                    updateNotificationForAddFriend();
                },
                error -> {
                    Log.w(TAG, "Failed to stop camera for AddFriendActivity", error);
                    cameraStoppedByAddFriend = false;
                }
        );
        req.setRetryPolicy(new DefaultRetryPolicy(4000, 0, 1f));
        requestQueue.add(req);
    }

    private void updateNotificationForAddFriend() {
        String text = "Camera temporarily stopped for face registration";
        getNotificationManager().notify(NOTIF_ID, buildNotification(text, false));
    }

    private void notify(String text, boolean highPriority) {
        Notification n = buildNotification(text, !lastHealthy || highPriority);
        getNotificationManager().notify(NOTIF_ID, n);
    }

    private NotificationManager getNotificationManager() {
        return (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Smart Glasses Monitoring",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.enableLights(true);
            channel.setLightColor(Color.BLUE);
            channel.enableVibration(true);
            getNotificationManager().createNotificationChannel(channel);
        }
    }

    private Notification buildNotification(String contentText, boolean problematic) {
        Intent openIntent = new Intent(this, MainActivity.class);
        PendingIntent contentPending = PendingIntent.getActivity(
                this, 0, openIntent,
                Build.VERSION.SDK_INT >= 31
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT
        );

        Intent stopIntent = new Intent(this, SmartGlassesForegroundService.class).setAction(ACTION_STOP);
        PendingIntent stopPending = PendingIntent.getService(
                this, 1, stopIntent,
                Build.VERSION.SDK_INT >= 31
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT
        );

        Intent checkIntent = new Intent(this, SmartGlassesForegroundService.class).setAction(ACTION_CHECK_NOW);
        PendingIntent checkPending = PendingIntent.getService(
                this, 2, checkIntent,
                Build.VERSION.SDK_INT >= 31
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT
        );

        Intent startCamIntent = new Intent(this, SmartGlassesForegroundService.class).setAction(ACTION_START_CAMERA);
        PendingIntent startCamPending = PendingIntent.getService(
                this, 3, startCamIntent,
                Build.VERSION.SDK_INT >= 31
                        ? PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
                        : PendingIntent.FLAG_UPDATE_CURRENT
        );

        NotificationCompat.Builder b = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(problematic ? R.drawable.ic_warning : R.drawable.ic_visibility_on)
                .setContentTitle("Blind Assistant")
                .setContentText(contentText)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(contentText))
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setContentIntent(contentPending)
                .addAction(R.drawable.ic_refresh, "Check now", checkPending)
                .addAction(R.drawable.ic_camera_on, "Start camera", startCamPending)
                .addAction(R.drawable.ic_stop, "Stop", stopPending)
                .setPriority(problematic ? NotificationCompat.PRIORITY_HIGH : NotificationCompat.PRIORITY_LOW);

        if(!cameraStoppedByAddFriend){
            b.addAction(R.drawable.ic_camera_on, "Start camera", startCamPending);
        }
        b.addAction(R.drawable.ic_stop, "Stop", stopPending);
        return b.build();
    }

    private void startCamera() {
        String url = SERVER_URL + "/api/camera/start";
        JsonObjectRequest req = new JsonObjectRequest(Request.Method.POST, url, null,
                response -> {
                    checkHealth(true);
                },
                error -> {
                    notify("Unable to start smart glasses camera.", true);
                }
        );
        req.setRetryPolicy(new DefaultRetryPolicy(4000, 0, 1f));
        requestQueue.add(req);
    }

    private void setupBackgroundSpeechRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) return;
        try {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
            speechRecognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {}
                @Override public void onBeginningOfSpeech() {}
                @Override public void onRmsChanged(float rmsdB) {}
                @Override public void onBufferReceived(byte[] buffer) {}
                @Override public void onEndOfSpeech() {}

                @Override public void onEvent(int eventType, Bundle params) {}
                @Override public void onPartialResults(Bundle partialResults) {}

                @Override
                public void onError(int error) {
                    isListening = false;
                    handler.postDelayed(() -> startListening(), 1500);
                }

                @Override
                public void onResults(Bundle results) {
                    handleVoiceResults(results);
                    isListening = false;
                    handler.postDelayed(() -> startListening(), 600);
                }
            });

            speechIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            String lang = "en-US";
            try {
                Locale loc = StringResources.getCurrentLocale();
                if (loc != null) lang = Build.VERSION.SDK_INT >= 21 ? loc.toLanguageTag() : loc.getLanguage();
            } catch (Exception ignored) {}
            speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang);
            speechIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);

            startListening();
        } catch (Exception e) {
            Log.w(TAG, "Speech recognizer setup failed", e);
        }
    }

    private void startListening() {
        if (speechRecognizer == null || isListening || !running) return;
        boolean uiActive = getSharedPreferences("blind_assistant_prefs", MODE_PRIVATE)
                .getBoolean("ui_recognition_active", false);
        if (uiActive) return;
        if (cameraStoppedByAddFriend) return;
        try {
            isListening = true;
            speechRecognizer.startListening(speechIntent);
        } catch (Exception e) {
            isListening = false;
        }
    }

    private void handleVoiceResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) return;
        String text = matches.get(0).toLowerCase().trim();

        if (text.contains("start") || text.contains("camera")) {
            startCamera();
            speakThrottled("Starting camera");
        } else if (text.contains("check") || text.contains("status")) {
            checkHealth(true);
            speakThrottled("Checking status");
        } else if (text.contains("stop")) {
            speakThrottled("Stopping monitoring");
            stopSelf();
        }
    }

    private void speakThrottled(String message) {
        long now = System.currentTimeMillis();
        if (now - lastTtsAtMs < TTS_THROTTLE_MS) return;
        lastTtsAtMs = now;
        try {
            if (tts != null) {
                Locale loc = StringResources.getCurrentLocale();
                if (loc != null) tts.setLanguage(loc);
                tts.speak(message, TextToSpeech.QUEUE_FLUSH, null, "SG_FG_TTS");
            }
        } catch (Exception ignored) {}
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            ttsReady = true;
            try {
                Locale loc = StringResources.getCurrentLocale();
                if (loc != null && tts != null) tts.setLanguage(loc);
            } catch (Exception ignored) {}
        }
    }
}


