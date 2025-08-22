package com.research.blindassistant;

import android.graphics.Bitmap;
import android.util.Base64;
import android.util.Log;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;

public class FaceRecognitionService {

    private static final String TAG = "FaceRecognitionService";
    private static final String SERVER_URL = "http://10.231.176.126:5000";

    private RequestQueue requestQueue;

    private FaceRecognitionCallback callback;

    public interface FaceRecognitionCallback {
        void onPersonRecognized(String name, float confidence, String message);
        void onPersonRegistered(String name, boolean success, String message);
        void onConnectionError(String error);
        void onServerHealthCheck(boolean healthy, int peopleCount);
    }

    public FaceRecognitionService(android.content.Context context) {
        requestQueue = Volley.newRequestQueue(context);
    }

    public void setCallback(FaceRecognitionCallback callback) {
        this.callback = callback;
    }

    public void checkServerHealth() {
        String url = SERVER_URL + "/api/health";

        JsonObjectRequest request = new JsonObjectRequest(
                Request.Method.GET, url, null,
                response -> {
                    try {
                        boolean healthy = "healthy".equals(response.getString("status"));
                        int peopleCount = response.getInt("people_count");

                        if (callback != null) {
                            callback.onServerHealthCheck(healthy, peopleCount);
                        }
                    } catch (JSONException e) {
                        Log.e(TAG, "Error parsing health response", e);
                        if (callback != null) {
                            callback.onConnectionError("Server response error");
                        }
                    }
                },
                error -> {
                    Log.e(TAG, "Health check failed", error);
                    if (callback != null) {
                        callback.onConnectionError("Cannot connect to recognition server");
                    }
                }
        );

        requestQueue.add(request);
    }

    public void recognizePerson(Bitmap image) {
        String url = SERVER_URL + "/api/recognize";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("image", bitmapToBase64(image));

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean recognized = response.getBoolean("recognized");
                            String name = response.optString("name", "Unknown");
                            double confidence = response.getDouble("confidence");
                            String message = response.getString("message");

                            if (callback != null) {
                                callback.onPersonRecognized(
                                        recognized ? name : null,
                                        (float) confidence,
                                        message
                                );
                            }
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing recognition response", e);
                            if (callback != null) {
                                callback.onConnectionError("Response parsing error");
                            }
                        }
                    },
                    error -> {
                        Log.e(TAG, "Recognition request failed", error);
                        if (callback != null) {
                            callback.onConnectionError("Recognition request failed");
                        }
                    }
            );

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating recognition request", e);
            if (callback != null) {
                callback.onConnectionError("Request creation error");
            }
        }
    }

    public void registerPerson(String name, Bitmap[] images) {
        String url = SERVER_URL + "/api/register";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("name", name);

            JSONArray imageArray = new JSONArray();
            for (Bitmap image : images) {
                imageArray.put(bitmapToBase64(image));
            }
            requestBody.put("images", imageArray);

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");
                            String message = response.getString("message");
                            int photosProcessed = response.getInt("photos_processed");

                            Log.d(TAG, "Registration result: " + message + " (" + photosProcessed + " photos)");

                            if (callback != null) {
                                callback.onPersonRegistered(name, success, message);
                            }
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing registration response", e);
                            if (callback != null) {
                                callback.onPersonRegistered(name, false, "Response parsing error");
                            }
                        }
                    },
                    error -> {
                        Log.e(TAG, "Registration request failed", error);
                        if (callback != null) {
                            callback.onPersonRegistered(name, false, "Registration request failed");
                        }
                    }
            );

            request.setRetryPolicy(new com.android.volley.DefaultRetryPolicy(
                    30000,
                    1,
                    com.android.volley.DefaultRetryPolicy.DEFAULT_BACKOFF_MULT
            ));

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating registration request", e);
            if (callback != null) {
                callback.onPersonRegistered(name, false, "Request creation error");
            }
        }
    }

    private String bitmapToBase64(Bitmap bitmap) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        bitmap.compress(Bitmap.CompressFormat.JPEG, 85, baos);
        byte[] imageBytes = baos.toByteArray();
        return Base64.encodeToString(imageBytes, Base64.DEFAULT);
    }

    public void cleanup() {
        if (requestQueue != null) {
            requestQueue.cancelAll(TAG);
        }
    }
}
