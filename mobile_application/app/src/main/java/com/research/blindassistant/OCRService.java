package com.research.blindassistant;

import android.content.Context;
import android.graphics.Bitmap;
import android.util.Base64;
import android.util.Log;
import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;

public class OCRService {

    private static final String TAG = "OCRService";
    private static final String SERVER_URL = "http://10.72.250.126:5002"; // Your Flask server URL

    private RequestQueue requestQueue;
    private OCRCallback callback;

    public interface OCRCallback {
        void onOCRResult(String documentType, float confidence, String extractedText,
                         float qualityScore, long processingTime);
        void onOCRError(String error);
        void onTTSResult(boolean success, String message);
    }

    public OCRService(Context context) {
        requestQueue = Volley.newRequestQueue(context);
    }

    public void setCallback(OCRCallback callback) {
        this.callback = callback;
    }

    public void processDocument(Bitmap image) {
        String url = SERVER_URL + "/api/ocr/process";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("image", bitmapToBase64(image));

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");
                            if (success) {
                                String documentType = response.getString("document_type");
                                float classificationConfidence = (float) response.getDouble("classification_confidence");
                                String extractedText = response.getString("extracted_text");
                                float qualityScore = (float) response.getDouble("quality_score");
                                long processingTime = response.getLong("processing_time");

                                if (callback != null) {
                                    callback.onOCRResult(documentType, classificationConfidence,
                                            extractedText, qualityScore, processingTime);
                                }
                            } else {
                                String error = response.getString("error");
                                if (callback != null) {
                                    callback.onOCRError(error);
                                }
                            }
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing OCR response", e);
                            if (callback != null) {
                                callback.onOCRError("Response parsing error");
                            }
                        }
                    },
                    error -> {
                        Log.e(TAG, "OCR request failed", error);
                        if (callback != null) {
                            callback.onOCRError("OCR request failed: " + error.getMessage());
                        }
                    }
            );

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating OCR request", e);
            if (callback != null) {
                callback.onOCRError("Request creation error");
            }
        }
    }

    public void speakText(String text) {
        String url = SERVER_URL + "/api/ocr/speak";

        try {
            JSONObject requestBody = new JSONObject();
            requestBody.put("text", text);

            JsonObjectRequest request = new JsonObjectRequest(
                    Request.Method.POST, url, requestBody,
                    response -> {
                        try {
                            boolean success = response.getBoolean("success");
                            String message = response.getString("message");

                            if (callback != null) {
                                callback.onTTSResult(success, message);
                            }
                        } catch (JSONException e) {
                            Log.e(TAG, "Error parsing TTS response", e);
                            if (callback != null) {
                                callback.onTTSResult(false, "Response parsing error");
                            }
                        }
                    },
                    error -> {
                        Log.e(TAG, "TTS request failed", error);
                        if (callback != null) {
                            callback.onTTSResult(false, "TTS request failed");
                        }
                    }
            );

            requestQueue.add(request);

        } catch (JSONException e) {
            Log.e(TAG, "Error creating TTS request", e);
            if (callback != null) {
                callback.onTTSResult(false, "Request creation error");
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