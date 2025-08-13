package com.research.blindassistant;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.Log;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.UUID;

public class MockSmartGlassesConnector implements SmartGlassesConnector {

    private static final String TAG = "MockSmartGlasses";

    private static final String CAMERA_SERVER_URL = "http://10.231.176.126:5001";

    private RequestQueue requestQueue;
    private Handler mainHandler;
    private SmartGlassesConnector.SmartGlassesCallback callback;
    private FaceRecognitionService faceRecognitionService;

    private boolean isConnected = false;
    private boolean isStreaming = false;
    private String clientId;

    private static final int FRAME_POLL_INTERVAL_MS = 200;
    private Runnable framePollingRunnable;

    public MockSmartGlassesConnector(android.content.Context context) {
        requestQueue = Volley.newRequestQueue(context);
        mainHandler = new Handler(Looper.getMainLooper());
        clientId = "android_" + UUID.randomUUID().toString().substring(0, 8);

        Log.d(TAG, "MockSmartGlassesConnector created with client ID: " + clientId);
    }

    @Override
    public void setCallback(SmartGlassesConnector.SmartGlassesCallback callback) {
        this.callback = callback;
    }

    @Override
    public void setFaceRecognitionService(FaceRecognitionService service) {
        this.faceRecognitionService = service;
    }

    @Override
    public void connect() {
        Log.d(TAG, "Attempting to connect to camera server: " + CAMERA_SERVER_URL);

        checkCameraServerHealth();
    }

    private void checkCameraServerHealth() {
        String url = CAMERA_SERVER_URL + "/api/camera/health";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        String status = response.getString("status");
                        boolean cameraAvailable = response.getBoolean("camera_available");

                        if ("healthy".equals(status) && cameraAvailable) {
                            Log.d(TAG, "Camera server is healthy, attempting connection");
                            connectToCamera();
                        } else {
                            Log.e(TAG, "Camera server not ready - status: " + status + ", camera: " + cameraAvailable);
                            notifyConnectionFailed("Camera server not ready");
                        }

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing health response", e);
                        notifyConnectionFailed("Health check failed");
                    }
                },
                error -> {
                    Log.e(TAG, "Camera server health check failed", error);
                    notifyConnectionFailed("Cannot reach camera server at " + CAMERA_SERVER_URL);
                }
        );

        request.setRetryPolicy(new com.android.volley.DefaultRetryPolicy(
                5000,
                0,
                1.0f
        ));

        requestQueue.add(request);
    }

    private void connectToCamera() {
        String url = CAMERA_SERVER_URL + "/api/camera/connect";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("client_id", clientId);

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");
                            String message = response.getString("message");

                            if (success) {
                                isConnected = true;
                                Log.d(TAG, "Successfully connected to camera: " + message);

                                if (callback != null) {
                                    callback.onConnectionStatusChanged(true, message);
                                }
                            } else {
                                Log.e(TAG, "Camera connection failed: " + message);
                                notifyConnectionFailed(message);
                            }

                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing connection response", e);
                            notifyConnectionFailed("Connection response error");
                        }
                    },
                    error -> {
                        Log.e(TAG, "Camera connection request failed", error);
                        notifyConnectionFailed("Connection request failed");
                    }
            );

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating connection request", e);
            notifyConnectionFailed("Request creation error");
        }
    }

    @Override
    public void startLiveFeed() {
        if (!isConnected) {
            Log.w(TAG, "Cannot start live feed - not connected");
            return;
        }

        if (isStreaming) {
            Log.w(TAG, "Live feed already started");
            return;
        }

        isStreaming = true;
        startFramePolling();

        Log.d(TAG, "Live feed started - polling frames every " + FRAME_POLL_INTERVAL_MS + "ms");
    }

    private void startFramePolling() {
        framePollingRunnable = new Runnable() {
            @Override
            public void run() {
                if (isStreaming && isConnected) {
                    pollForFrame();

                    mainHandler.postDelayed(this, FRAME_POLL_INTERVAL_MS);
                }
            }
        };

        mainHandler.post(framePollingRunnable);
    }

    private void pollForFrame() {
        String url = CAMERA_SERVER_URL + "/api/camera/frame";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        boolean success = response.getBoolean("success");

                        if (success) {
                            JSONObject frameData = response.getJSONObject("frame_data");
                            String imageBase64 = frameData.getString("image");
                            double timestamp = frameData.getDouble("timestamp");

                            Bitmap frame = base64ToBitmap(imageBase64);

                            if (frame != null && callback != null) {
                                Log.d(TAG, "Frame received and forwarded: " + frame.getWidth() + "x" + frame.getHeight());
                                callback.onFrameReceived(frame, (long)(timestamp * 1000), 1.0);
                            } else {
                                Log.w(TAG, "Frame is null or callback not set");
                            }
                        }

                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing frame response", e);
                    }
                },
                error -> {
                    if (Math.random() < 0.1) {
                        Log.w(TAG, "Frame polling error (occasional logging)");
                    }
                }
        );

        request.setRetryPolicy(new com.android.volley.DefaultRetryPolicy(
                2000,
                0,
                1.0f
        ));

        requestQueue.add(request);
    }

    @Override
    public void stopLiveFeed() {
        if (!isStreaming) {
            return;
        }

        isStreaming = false;

        if (framePollingRunnable != null) {
            mainHandler.removeCallbacks(framePollingRunnable);
            framePollingRunnable = null;
        }

        if (callback != null) {
            callback.onFeedStopped();
        }

        Log.d(TAG, "Live feed stopped");
    }

    @Override
    public void sendRecognitionData(String personName, String[] imagesBase64) {
        Log.d(TAG, "Sending recognition data for: " + personName + " with " + imagesBase64.length + " images");

        if (faceRecognitionService != null) {
            registerPersonWithBase64Images(personName, imagesBase64);
        } else {
            Log.e(TAG, "Face recognition service not set");
            if (callback != null) {
                callback.onError("Face recognition service not available");
            }
        }
    }

    private void registerPersonWithBase64Images(String name, String[] imagesBase64) {
        String url = "http://10.231.176.126:5000";

        try {
            Log.d(TAG, "Preparing registration request for: " + name);
            Log.d(TAG, "Number of images: " + imagesBase64.length);

            JSONObject requestBody = new JSONObject();
            requestBody.put("name", name.trim());

            JSONArray imageArray = new JSONArray();

            for (int i = 0; i < imagesBase64.length; i++) {
                String imageBase64 = imagesBase64[i];

                if (imageBase64 == null || imageBase64.trim().isEmpty()) {
                    Log.w(TAG, "Skipping empty image at index " + i);
                    continue;
                }

                String cleanBase64 = imageBase64.replaceAll("\\s+", "");

                if (cleanBase64.length() < 100) {
                    Log.w(TAG, "Image " + i + " seems too small, length: " + cleanBase64.length());
                    continue;
                }

                Log.d(TAG, "Adding image " + i + " to request, length: " + cleanBase64.length());
                imageArray.put(cleanBase64);
            }

            if (imageArray.length() == 0) {
                Log.e(TAG, "No valid images to send for registration");
                notifyRegistrationError("No valid images to register");
                return;
            }

            requestBody.put("images", imageArray);

            Log.d(TAG, "Final request body - name: " + name + ", images count: " + imageArray.length());

            if (imageArray.length() > 0) {
                try {
                    String firstImage = imageArray.getString(0);
                    String sample = firstImage.substring(0, Math.min(100, firstImage.length()));
                    Log.d(TAG, "First image sample (100 chars): " + sample + "...");
                } catch (Exception e) {
                    Log.w(TAG, "Could not log image sample", e);
                }
            }

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            Log.d(TAG, "Registration response received: " + response.toString());

                            boolean success = response.getBoolean("success");
                            String message = response.getString("message");

                            Log.d(TAG, "Registration result: success=" + success + ", message=" + message);

                            if (callback != null) {
                                if (success) {
                                    callback.onPersonRegistered(name);
                                } else {
                                    callback.onError("Registration failed: " + message);
                                }
                            }

                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing registration response", e);
                            notifyRegistrationError("Response parsing error: " + e.getMessage());
                        }
                    },
                    error -> {
                        Log.e(TAG, "Registration request failed", error);

                        String errorDetails = "Unknown error";
                        if (error.networkResponse != null) {
                            errorDetails = "HTTP " + error.networkResponse.statusCode;
                            if (error.networkResponse.data != null) {
                                try {
                                    String responseBody = new String(error.networkResponse.data, "UTF-8");
                                    Log.e(TAG, "Error response body: " + responseBody);
                                    errorDetails += " - " + responseBody;
                                } catch (Exception e) {
                                    Log.e(TAG, "Could not parse error response body", e);
                                }
                            }
                        }

                        notifyRegistrationError("Registration request failed: " + errorDetails);
                    }
            );

            request.setRetryPolicy(new com.android.volley.DefaultRetryPolicy(
                    30000,
                    1,
                    1.0f
            ));

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating registration request", e);
            notifyRegistrationError("Request creation error: " + e.getMessage());
        }
    }

    @Override
    public void disconnect() {
        Log.d(TAG, "Disconnecting from camera server");

        stopLiveFeed();

        if (isConnected) {
            disconnectFromCamera();
        }
    }

    private void disconnectFromCamera() {
        String url = CAMERA_SERVER_URL + "/api/camera/disconnect";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("client_id", clientId);

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        isConnected = false;
                        Log.d(TAG, "Successfully disconnected from camera");
                    },
                    error -> {
                        isConnected = false;
                        Log.w(TAG, "Disconnect request failed, but marking as disconnected");
                    }
            );

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating disconnect request", e);
            isConnected = false;
        }
    }

    @Override
    public void cleanup() {
        Log.d(TAG, "Cleaning up MockSmartGlassesConnector");

        disconnect();

        if (requestQueue != null) {
            requestQueue.cancelAll(TAG);
        }

        callback = null;
        faceRecognitionService = null;
    }

    @Override
    public boolean isConnected() {
        return isConnected;
    }

    @Override
    public boolean isReceivingFeed() {
        return isStreaming;
    }

    private void notifyConnectionFailed(String error) {
        isConnected = false;

        if (callback != null) {
            callback.onConnectionStatusChanged(false, error);
        }
    }

    private void notifyRegistrationError(String error) {
        Log.e(TAG, "Registration error: " + error);
        if (callback != null) {
            callback.onError("Registration error: " + error);
        }
    }

    private Bitmap base64ToBitmap(String base64String) {
        try {
            byte[] decodedBytes = Base64.decode(base64String, Base64.DEFAULT);
            return BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.length);
        } catch (Exception e) {
            Log.e(TAG, "Error decoding base64 to bitmap", e);
            return null;
        }
    }

    public String getClientId() {
        return clientId;
    }
}