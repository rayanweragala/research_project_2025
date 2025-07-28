package com.research.blindassistant;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.Log;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SmartGlassesConnector {
    private static final String TAG = "SmartGlassesConnector";

    private static final String RASPBERRY_PI_IP = "192.168.1.100";
    private static final int PORT = 8080;
    private static final String BASE_URL = "http://" + RASPBERRY_PI_IP + ":" + PORT;

    private static final String LIVE_FEED_ENDPOINT = "/api/live-feed";
    private static final String START_CAPTURE_ENDPOINT = "/api/start-capture";
    private static final String STOP_CAPTURE_ENDPOINT = "/api/stop-capture";
    private static final String STATUS_ENDPOINT = "/api/status";

    private ExecutorService executorService;
    private Handler mainHandler;
    private boolean isConnected;
    private boolean isReceivingFeed;
    private SmartGlassesCallback callback;

    public SmartGlassesConnector() {
        executorService = Executors.newFixedThreadPool(3);
        mainHandler = new Handler(Looper.getMainLooper());
        isConnected = false;
        isReceivingFeed = false;
    }

    public void setCallback(SmartGlassesCallback callback) {
        this.callback = callback;
    }

    public void connect() {
        executorService.execute(() -> {
            try {
                URL url = new URL(BASE_URL + STATUS_ENDPOINT);
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);

                int responseCode = connection.getResponseCode();
                if (responseCode == 200) {
                    isConnected = true;
                    mainHandler.post(() -> {
                        if (callback != null) {
                            callback.onConnectionStatusChanged(true, "Smart glasses connected");
                        }
                    });
                    Log.d(TAG, "Successfully connected to smart glasses");
                } else {
                    throw new IOException("HTTP " + responseCode);
                }

                connection.disconnect();

            } catch (Exception e) {
                Log.e(TAG, "Failed to connect to smart glasses", e);
                isConnected = false;
                mainHandler.post(() -> {
                    if (callback != null) {
                        callback.onConnectionStatusChanged(false, "Connection failed: " + e.getMessage());
                    }
                });
            }
        });
    }

    public void startLiveFeed() {
        if (!isConnected) {
            if (callback != null) {
                callback.onError("Not connected to smart glasses");
            }
            return;
        }

        if (isReceivingFeed) {
            Log.w(TAG, "Live feed already running");
            return;
        }

        isReceivingFeed = true;

        executorService.execute(() -> {
            try {
                sendStartCaptureCommand();

                receiveLiveFeed();

            } catch (Exception e) {
                Log.e(TAG, "Error in live feed", e);
                isReceivingFeed = false;
                mainHandler.post(() -> {
                    if (callback != null) {
                        callback.onError("Live feed error: " + e.getMessage());
                    }
                });
            }
        });
    }

    private void sendStartCaptureCommand() throws IOException {
        URL url = new URL(BASE_URL + START_CAPTURE_ENDPOINT);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("POST");
        connection.setRequestProperty("Content-Type", "application/json");
        connection.setDoOutput(true);

        JSONObject params = new JSONObject();
        try {
            params.put("mode", "live_feed");
            params.put("fps", 2);
            params.put("quality", "high");
        } catch (JSONException e) {
            Log.e(TAG, "Error creating JSON params", e);
        }

        OutputStream os = connection.getOutputStream();
        os.write(params.toString().getBytes());
        os.flush();
        os.close();

        int responseCode = connection.getResponseCode();
        if (responseCode != 200) {
            throw new IOException("Failed to start capture: HTTP " + responseCode);
        }

        connection.disconnect();
        Log.d(TAG, "Started capture on smart glasses");
    }

    private void receiveLiveFeed() {
        while (isReceivingFeed && isConnected) {
            try {
                URL url = new URL(BASE_URL + LIVE_FEED_ENDPOINT);
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(5000);

                int responseCode = connection.getResponseCode();
                if (responseCode == 200) {
                    BufferedReader reader = new BufferedReader(
                            new InputStreamReader(connection.getInputStream()));
                    StringBuilder response = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    reader.close();

                    JSONObject frameData = new JSONObject(response.toString());
                    processFrameData(frameData);

                } else if (responseCode == 204) {
                    Thread.sleep(500);
                } else {
                    Log.w(TAG, "Unexpected response code: " + responseCode);
                    Thread.sleep(1000);
                }

                connection.disconnect();

            } catch (InterruptedException e) {
                Log.d(TAG, "Live feed interrupted");
                break;
            } catch (Exception e) {
                Log.e(TAG, "Error receiving live feed", e);

                try {
                    Thread.sleep(2000);
                } catch (InterruptedException ie) {
                    break;
                }
            }
        }

        Log.d(TAG, "Live feed stopped");
    }

    private void processFrameData(JSONObject frameData) {
        try {
            String imageBase64 = frameData.getString("image");
            long timestamp = frameData.getLong("timestamp");
            double confidence = frameData.optDouble("confidence", 1.0);

            byte[] imageBytes = Base64.decode(imageBase64, Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.length);

            if (bitmap != null) {

                mainHandler.post(() -> {
                    if (callback != null && isReceivingFeed) {
                        callback.onFrameReceived(bitmap, timestamp, confidence);
                    }
                });
            } else {
                Log.w(TAG, "Failed to decode frame image");
            }

        } catch (JSONException e) {
            Log.e(TAG, "Error parsing frame data", e);
        } catch (Exception e) {
            Log.e(TAG, "Error processing frame", e);
        }
    }

    public void stopLiveFeed() {
        if (!isReceivingFeed) {
            return;
        }

        isReceivingFeed = false;

        executorService.execute(() -> {
            try {
                URL url = new URL(BASE_URL + STOP_CAPTURE_ENDPOINT);
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(3000);

                int responseCode = connection.getResponseCode();
                connection.disconnect();

                Log.d(TAG, "Stop capture response: " + responseCode);

            } catch (Exception e) {
                Log.e(TAG, "Error stopping capture", e);
            }

            mainHandler.post(() -> {
                if (callback != null) {
                    callback.onFeedStopped();
                }
            });
        });
    }

    public void disconnect() {
        stopLiveFeed();
        isConnected = false;

        mainHandler.post(() -> {
            if (callback != null) {
                callback.onConnectionStatusChanged(false, "Disconnected");
            }
        });
    }

    public boolean isConnected() {
        return isConnected;
    }

    public boolean isReceivingFeed() {
        return isReceivingFeed;
    }

    public void sendRecognitionData(String personName, String[] imageBase64Array) {
        if (!isConnected) {
            if (callback != null) {
                callback.onError("Not connected to smart glasses");
            }
            return;
        }

        executorService.execute(() -> {
            try {
                URL url = new URL(BASE_URL + "/api/register-person");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setDoOutput(true);

                JSONObject data = new JSONObject();
                data.put("name", personName);
                data.put("images", imageBase64Array);
                data.put("timestamp", System.currentTimeMillis());

                OutputStream os = connection.getOutputStream();
                os.write(data.toString().getBytes());
                os.flush();
                os.close();

                int responseCode = connection.getResponseCode();
                connection.disconnect();

                final boolean success = responseCode == 200;
                mainHandler.post(() -> {
                    if (callback != null) {
                        if (success) {
                            callback.onPersonRegistered(personName);
                        } else {
                            callback.onError("Failed to register person on smart glasses");
                        }
                    }
                });

            } catch (Exception e) {
                Log.e(TAG, "Error sending recognition data", e);
                mainHandler.post(() -> {
                    if (callback != null) {
                        callback.onError("Error registering person: " + e.getMessage());
                    }
                });
            }
        });
    }

    public void cleanup() {
        disconnect();

        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }
    }

    public interface SmartGlassesCallback {
        void onConnectionStatusChanged(boolean connected, String message);
        void onFrameReceived(Bitmap frame, long timestamp, double confidence);
        void onFeedStopped();
        void onPersonRegistered(String personName);
        void onError(String error);
    }
}