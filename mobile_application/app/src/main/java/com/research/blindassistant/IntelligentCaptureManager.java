package com.research.blindassistant;

import android.graphics.Bitmap;
import android.os.Looper;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import android.os.Handler;
import android.util.Log;

public class IntelligentCaptureManager {
    private static final String TAG = "IntelligentCaptureManager";

    private static final int MIN_CAPTURES = 3;
    private static final int MAX_CAPTURES = 6;
    private static final long CAPTURE_COOLDOWN_MS = 1500;
    private static final float ANGLE_DIVERSITY_THRESHOLD = 20f;
    private static final float POSITION_DIVERSITY_THRESHOLD = 0.3f;

    private FaceQualityAnalyzer qualityAnalyzer;
    private android.os.Handler mainHandler;
    private CaptureProgressCallback callback;

    private List<CapturedFace> capturedFaces;
    private Set<String> capturedAngles;
    private long lastCaptureTime;
    private boolean isCapturing;
    private String personName;
    private long captureStartTime;


    public IntelligentCaptureManager() {
        qualityAnalyzer = new FaceQualityAnalyzer();
        mainHandler = new Handler(Looper.getMainLooper());
        capturedFaces = new ArrayList<>();
        capturedAngles = new HashSet<>();
        lastCaptureTime = 0;
        isCapturing = false;
    }

    public void startIntelligentCapture(String personName, CaptureProgressCallback callback) {
        this.personName = personName;
        this.callback = callback;
        this.isCapturing = true;
        this.captureStartTime = System.currentTimeMillis();

        capturedFaces.clear();
        capturedAngles.clear();
        lastCaptureTime = 0;

        if (callback != null) {
            callback.onCaptureStarted(personName);
            callback.onProgressUpdate(0, MIN_CAPTURES, "Looking for " + personName + "...");
        }

        Log.d(TAG, "Started intelligent capture for: " + personName);
    }

    public void processCandidateFrame(Bitmap frame) {
        if (!isCapturing || frame == null) return;

        long currentTime = System.currentTimeMillis();
        if (currentTime - lastCaptureTime < CAPTURE_COOLDOWN_MS) {
            return;
        }

        Log.d(TAG, "Processing candidate frame: " + frame.getWidth() + "x" + frame.getHeight());


        qualityAnalyzer.analyzeFaceQuality(frame, result -> {
            if (!isCapturing) return;

            mainHandler.post(() -> handleQualityResult(frame, result));
        });
    }

    private void handleQualityResult(Bitmap frame, FaceQualityAnalyzer.FaceQualityResult result) {
        if (!isCapturing) return;

        Log.d(TAG, String.format("Quality result: good=%b, score=%.2f, feedback=%s",
                result.isGoodQuality, result.qualityScore, result.feedback));

        if (callback != null) {
            callback.onRealTimeFeedback(result.feedback, result.qualityScore);
        }

        boolean shouldCapture = false;

        if (result.isGoodQuality) {
            shouldCapture = shouldCaptureThisAngle(result.faceAngle, result.facePosition);
        } else if (result.qualityScore > 0.3f && capturedFaces.size() < MIN_CAPTURES) {
            shouldCapture = shouldCaptureThisAngle(result.faceAngle, result.facePosition);
            Log.d(TAG, "Accepting medium quality capture to meet minimum requirement");
        } else if (capturedFaces.isEmpty() && result.qualityScore > 0.2f) {
            shouldCapture = true;
            Log.d(TAG, "Accepting first capture with lower quality threshold");
        }

        long captureTime = System.currentTimeMillis() - captureStartTime;
        if (captureTime > 15000 && capturedFaces.size() < MIN_CAPTURES && result.qualityScore > 0.2f) {
            shouldCapture = true;
            Log.d(TAG, "Time-based fallback: accepting lower quality after 15 seconds");
        }

        if (shouldCapture) {
            captureFrame(frame, result);
        }
    }

    private boolean shouldCaptureThisAngle(String faceAngle, String facePosition) {
        if (capturedFaces.size() < 2) {
            return true;
        }

        if (capturedAngles.contains(faceAngle)) {
            Log.d(TAG, "Angle " + faceAngle + " already captured, checking position diversity");
            return isPositionDiverse(facePosition);
        }

        return true;
    }

    private boolean isPositionDiverse(String facePosition) {
        String[] coords = facePosition.split(",");
        if (coords.length != 2) return true;

        try {
            float newX = Float.parseFloat(coords[0]);
            float newY = Float.parseFloat(coords[1]);

            for (CapturedFace captured : capturedFaces) {
                String[] capturedCoords = captured.facePosition.split(",");
                if (capturedCoords.length == 2) {
                    float capturedX = Float.parseFloat(capturedCoords[0]);
                    float capturedY = Float.parseFloat(capturedCoords[1]);

                    float distance = (float) Math.sqrt(
                            Math.pow(newX - capturedX, 2) + Math.pow(newY - capturedY, 2)
                    );

                    if (distance < POSITION_DIVERSITY_THRESHOLD) {
                        Log.d(TAG, String.format("Position too similar: distance=%.2f, threshold=%.2f",
                                distance, POSITION_DIVERSITY_THRESHOLD));
                        return false;
                    }
                }
            }
        } catch (NumberFormatException e) {
            Log.w(TAG, "Failed to parse position coordinates: " + facePosition);
        }

        return true;
    }

    private void captureFrame(Bitmap frame, FaceQualityAnalyzer.FaceQualityResult result) {
        lastCaptureTime = System.currentTimeMillis();

        CapturedFace capturedFace = new CapturedFace(
                frame.copy(frame.getConfig(), false),
                result.faceAngle,
                result.facePosition,
                result.qualityScore,
                System.currentTimeMillis()
        );

        capturedFaces.add(capturedFace);
        capturedAngles.add(result.faceAngle);

        Log.d(TAG, String.format("Successfully captured frame %d: angle=%s, quality=%.2f, position=%s",
                capturedFaces.size(), result.faceAngle, result.qualityScore, result.facePosition));

        if (callback != null) {
            String captureMessage = generateCaptureMessage(capturedFaces.size(), result.faceAngle);
            callback.onSuccessfulCapture(capturedFaces.size(), captureMessage);
            callback.onProgressUpdate(capturedFaces.size(), MIN_CAPTURES,
                    getProgressMessage(capturedFaces.size()));
        }

        if (shouldCompleteCapture()) {
            completeCapture();
        }
    }

    private String generateCaptureMessage(int captureNumber, String angle) {
        String[] messages = {
                "Perfect shot!",
                "Excellent angle!",
                "Great capture!",
                "Beautiful photo!",
                "Outstanding!",
                "Superb quality!",
                "Fantastic shot!",
                "Wonderful capture!"
        };

        String baseMessage = messages[captureNumber % messages.length];
        String angleDescription = getAngleDescription(angle);

        return baseMessage + " Got " + angleDescription + ".";
    }

    private String getAngleDescription(String angle) {
        switch (angle) {
            case "front": return "frontal view";
            case "left_profile": return "left profile";
            case "right_profile": return "right profile";
            case "slight_left": return "slight left turn";
            case "slight_right": return "slight right turn";
            default: return "good angle";
        }
    }

    private String getProgressMessage(int captureCount) {
        if (captureCount < MIN_CAPTURES) {
            int remaining = MIN_CAPTURES - captureCount;
            return "Need " + remaining + " more shots. Keep looking at the glasses.";
        } else {
            return "Getting bonus shots for better accuracy...";
        }
    }

    private boolean shouldCompleteCapture() {
        if (capturedFaces.size() < MIN_CAPTURES) {
            return false;
        }

        if (capturedFaces.size() >= MAX_CAPTURES) {
            Log.d(TAG, "Completing capture: reached maximum captures");
            return true;
        }

        if (capturedAngles.size() >= 3) {
            Log.d(TAG, "Completing capture: captured 3+ different angles");
            return true;
        }

        long timeSinceLastCapture = System.currentTimeMillis() - lastCaptureTime;
        if (timeSinceLastCapture > 8000 && capturedFaces.size() >= MIN_CAPTURES) {
            Log.d(TAG, "Completing capture: timeout after minimum captures");
            return true;
        }

        long totalCaptureTime = System.currentTimeMillis() - captureStartTime;
        if (totalCaptureTime > 30000) {
            Log.d(TAG, "Completing capture: total time limit reached");
            return true;
        }

        return false;
    }

    private void completeCapture() {
        isCapturing = false;

        Log.d(TAG, String.format("Completing capture for %s with %d photos, %d angles",
                personName, capturedFaces.size(), capturedAngles.size()));

        if (callback != null) {
            capturedFaces.sort((a, b) -> Float.compare(b.qualityScore, a.qualityScore));

            callback.onCaptureCompleted(personName, capturedFaces);
        }
    }

    public void stopCapture() {
        if (isCapturing) {
            isCapturing = false;

            if (callback != null) {
                callback.onCaptureStopped("Capture stopped by user");
            }

            Log.d(TAG, "Capture stopped by user");
        }
    }

    public boolean isCapturing() {
        return isCapturing;
    }

    public int getCaptureCount() {
        return capturedFaces.size();
    }

    public void cleanup() {
        stopCapture();

        for (CapturedFace face : capturedFaces) {
            if (face.bitmap != null && !face.bitmap.isRecycled()) {
                face.bitmap.recycle();
            }
        }
        capturedFaces.clear();

        if (qualityAnalyzer != null) {
            qualityAnalyzer.cleanup();
        }
    }
    public static class CapturedFace {
        public final Bitmap bitmap;
        public final String faceAngle;
        public final String facePosition;
        public final float qualityScore;
        public final long timestamp;

        public CapturedFace(Bitmap bitmap, String faceAngle, String facePosition,
                            float qualityScore, long timestamp) {
            this.bitmap = bitmap;
            this.faceAngle = faceAngle;
            this.facePosition = facePosition;
            this.qualityScore = qualityScore;
            this.timestamp = timestamp;
        }
    }
    public interface CaptureProgressCallback {
        void onCaptureStarted(String personName);
        void onRealTimeFeedback(String feedback, float qualityScore);
        void onSuccessfulCapture(int captureNumber, String message);
        void onProgressUpdate(int currentCount, int targetCount, String progressMessage);
        void onCaptureCompleted(String personName, List<CapturedFace> capturedFaces);
        void onCaptureStopped(String reason);
        void onError(String error);
    }
}
