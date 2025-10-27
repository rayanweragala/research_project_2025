package com.research.blindassistant;

import android.graphics.Bitmap;
import android.os.Looper;

import java.util.*;

import android.os.Handler;
import android.util.Log;
import androidx.appcompat.app.AppCompatActivity;

public class IntelligentCaptureManager extends AppCompatActivity {
    private static final String TAG = "IntelligentCaptureManager";

    private static final int MIN_CAPTURES = 5;
    private static final int MAX_CAPTURES = 12;
    private static final int TARGET_HIGH_QUALITY = 3;
    private static final long CAPTURE_COOLDOWN_MS = 1200;
    private static final long MIN_TIME_BETWEEN_ANGLES = 2000;
    private static final float HIGH_QUALITY_THRESHOLD = 0.7f;
    private static final float ACCEPTABLE_QUALITY_THRESHOLD = 0.5f;
    private static final float EMERGENCY_QUALITY_THRESHOLD = 0.3f;

    private static final float MIN_POSE_DIFFERENCE = 5f;
    private static final float MIN_POSITION_DIFFERENCE = 0.1f;
    private FaceQualityAnalyzer qualityAnalyzer;
    private android.os.Handler mainHandler;
    private CaptureProgressCallback callback;

    private List<CapturedFace> capturedFaces;
    private Map<String, Long> lastCaptureByAngle;
    private Set<String> requiredAngles;
    private long lastCaptureTime;
    private boolean isCapturing;
    private String personName;
    private long captureStartTime;
    private int highQualityCount;
    private int consecutiveRejections;

    private float currentQualityThreshold;
    private boolean emergencyMode;
    private static final int MAX_CONSECUTIVE_REJECTIONS = 15;
    private static final long EMERGENCY_MODE_TIMEOUT = 20000;
    private volatile boolean isProcessingFrame = false;
    private static final long FRAME_PROCESSING_TIMEOUT = 500;

    public IntelligentCaptureManager() {
        qualityAnalyzer = new FaceQualityAnalyzer();
        mainHandler = new Handler(Looper.getMainLooper());
        capturedFaces = new ArrayList<>();
        lastCaptureByAngle = new HashMap<>();
        requiredAngles = new HashSet<>();
        setupRequiredAngles();
        resetCapture();
    }

    private void setupRequiredAngles() {
        requiredAngles.add("frontal");
//        requiredAngles.add("slight_left");
        requiredAngles.add("slight_right");

//        requiredAngles.add("left_profile");
//        requiredAngles.add("right_profile");
    }

    private void resetCapture() {
        capturedFaces.clear();
        lastCaptureByAngle.clear();
        lastCaptureTime = 0;
        highQualityCount = 0;
        consecutiveRejections = 0;
        currentQualityThreshold = ACCEPTABLE_QUALITY_THRESHOLD;
        emergencyMode = false;
    }
    public void startIntelligentCapture(String personName, CaptureProgressCallback callback) {
        this.personName = personName;
        this.callback = callback;
        this.isCapturing = true;
        this.captureStartTime = System.currentTimeMillis();

        resetCapture();

        if (callback != null) {
            callback.onCaptureStarted(personName);
            callback.onProgressUpdate(0, MIN_CAPTURES,
                    "Looking for " + personName + ". I need high-quality images from multiple angles.");
        }

        Log.d(TAG, "Started intelligent capture for: " + personName);
    }

    public void processCandidateFrame(Bitmap frame) {
        if (!isCapturing || frame == null) return;

        long currentTime = System.currentTimeMillis();
        if (currentTime - lastCaptureTime < CAPTURE_COOLDOWN_MS) {
            return;
        }

        if (isProcessingFrame) {
            return;
        }

        checkEmergencyMode(currentTime);

        isProcessingFrame = true;

        qualityAnalyzer.analyzeFaceQuality(frame, (result) -> {
            isProcessingFrame = false;
            handleQualityResult(result);
        });
    }

    private void checkEmergencyMode(long currentTime) {
        if (!emergencyMode && currentTime - captureStartTime > EMERGENCY_MODE_TIMEOUT) {
            if (capturedFaces.size() < MIN_CAPTURES) {
                emergencyMode = true;
                currentQualityThreshold = EMERGENCY_QUALITY_THRESHOLD;
                Log.d(TAG, "Entering emergency mode - lowering quality threshold");

                if (callback != null) {
                    callback.onRealTimeFeedback(
                            "Having trouble getting good shots. I'll accept lower quality images now.",
                            0.5f
                    );
                }
            }
        }
    }
    private void handleQualityResult(FaceQualityAnalyzer.FaceQualityResult result) {
        if (!isCapturing) return;

        mainHandler.post(() -> {
            try {
                if (callback != null) {
                    callback.onRealTimeFeedback(result.feedback, result.qualityScore);
                    if (Math.random() < 0.3) {
                        callback.onTechnicalFeedback(result.technicalFeedback, result.metrics);
                    }
                }

                boolean shouldCapture = evaluateCaptureDecision(result);

                if (shouldCapture) {
                    performCapture(result);
                    consecutiveRejections = 0;
                } else {
                    consecutiveRejections++;
                    handleRejection(result);
                }

                if (shouldCompleteCapture()) {
                    completeCapture();
                }
            } catch (Exception e) {
                Log.e(TAG, "Error handling quality result", e);
            }
        });
    }

    private boolean evaluateCaptureDecision(FaceQualityAnalyzer.FaceQualityResult result) {
        if (capturedFaces.size() < 2) {
            Log.d(TAG, "Accepted: Need at least 2 images for server");
            return true;
        }

        if (result.qualityScore < currentQualityThreshold) {
            Log.d(TAG, String.format("Rejected: Quality %.2f below threshold %.2f",
                    result.qualityScore, currentQualityThreshold));
            return false;
        }

        if ("frontal".equals(result.faceAngle)) {
            if (result.qualityScore >= 0.4f) {
                Log.d(TAG, "Accepted: Frontal face with acceptable quality");
                return true;
            }
        }

        Long lastAngleCapture = lastCaptureByAngle.get(result.faceAngle);
        long currentTime = System.currentTimeMillis();
        if (lastAngleCapture != null &&
                (currentTime - lastAngleCapture) < MIN_TIME_BETWEEN_ANGLES) {
            Log.d(TAG, "Rejected: Same angle captured too recently");
            return false;
        }

        if (capturedFaces.size() >= MIN_CAPTURES) {
            if (!isPoseDiverse(result)) {
                Log.d(TAG, "Rejected: Pose not diverse enough");
                return false;
            }
        }

        Log.d(TAG, "Accepted: Passed all checks");
        return true;
    }

    private boolean isPoseDiverse(FaceQualityAnalyzer.FaceQualityResult result) {
        if (capturedFaces.isEmpty()) return true;

        float[] newPose = result.metrics.headPose;

        for (CapturedFace captured : capturedFaces) {
            float[] existingPose = captured.headPose;

            float yawDiff = Math.abs(newPose[1] - existingPose[1]);
            float pitchDiff = Math.abs(newPose[0] - existingPose[0]);

            if (yawDiff < MIN_POSE_DIFFERENCE && pitchDiff < MIN_POSE_DIFFERENCE) {
                return false;
            }
        }
        return true;
    }

    private boolean isPositionDiverse(String facePosition) {
        if (capturedFaces.isEmpty()) return true;

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

                    if (distance < MIN_POSITION_DIFFERENCE) {
                        return false;
                    }
                }
            }
        } catch (NumberFormatException e) {
            Log.w(TAG, "Failed to parse position coordinates: " + facePosition);
        }

        return true;
    }

    private boolean hasAngle(String angle) {
        return capturedFaces.stream().anyMatch(face -> angle.equals(face.faceAngle));
    }
    private void handleRejection(FaceQualityAnalyzer.FaceQualityResult result) {
        if (consecutiveRejections > MAX_CONSECUTIVE_REJECTIONS && !emergencyMode) {
            emergencyMode = true;
            currentQualityThreshold = EMERGENCY_QUALITY_THRESHOLD;

            if (callback != null) {
                callback.onRealTimeFeedback(
                        "Adjusting requirements to capture images. Please hold steady.",
                        0.4f
                );
            }
            Log.d(TAG, "Too many consecutive rejections - entering emergency mode");
        }
    }
    private void performCapture(FaceQualityAnalyzer.FaceQualityResult result) {
        lastCaptureTime = System.currentTimeMillis();
        lastCaptureByAngle.put(result.faceAngle, lastCaptureTime);

        Bitmap captureImage = result.processedFace != null ?
                result.processedFace :
                extractFaceRegion(result);

        CapturedFace capturedFace = new CapturedFace(
                captureImage,
                result.faceAngle,
                result.facePosition,
                result.qualityScore,
                result.metrics,
                result.metrics.headPose,
                System.currentTimeMillis()
        );

        capturedFaces.add(capturedFace);

        if (result.qualityScore >= HIGH_QUALITY_THRESHOLD) {
            highQualityCount++;
        }

        Log.d(TAG, String.format(
                "Captured frame %d: angle=%s, quality=%.2f, high_quality_count=%d",
                capturedFaces.size(), result.faceAngle, result.qualityScore, highQualityCount
        ));

        if (callback != null) {
            String captureMessage = generateEnhancedCaptureMessage(capturedFaces.size(), result);
            callback.onSuccessfulCapture(capturedFaces.size(), captureMessage);
            callback.onProgressUpdate(
                    capturedFaces.size(),
                    MIN_CAPTURES,
                    generateProgressMessage()
            );
        }
    }

    private Bitmap extractFaceRegion(FaceQualityAnalyzer.FaceQualityResult result) {
        // This would need access to the original frame - implementation depends on your architecture
        // For now, return null and rely on processedFace from the analyzer
        return null;
    }

    private String getProgressMessage(int captureCount) {
        if (captureCount < MIN_CAPTURES) {
            int remaining = MIN_CAPTURES - captureCount;
            return "Need " + remaining + " more shots. Keep looking at the glasses.";
        } else {
            return "Getting bonus shots for better accuracy...";
        }
    }

    private String generateEnhancedCaptureMessage(int captureNumber,
                                                  FaceQualityAnalyzer.FaceQualityResult result) {
        String qualityDesc = getQualityDescription(result.qualityScore);
        String angleDesc = getAngleDescription(result.faceAngle);

        String[] enthusiasticWords = {"Excellent!", "Perfect!", "Outstanding!", "Superb!", "Fantastic!"};
        String[] goodWords = {"Great!", "Nice!", "Good shot!", "Well done!"};

        String[] words = result.qualityScore >= HIGH_QUALITY_THRESHOLD ?
                enthusiasticWords : goodWords;

        String baseMessage = words[captureNumber % words.length];
        return String.format("%s %s %s captured.", baseMessage, qualityDesc, angleDesc);
    }

    private String getQualityDescription(float quality) {
        if (quality >= 0.9f) return "Premium quality";
        if (quality >= 0.8f) return "High quality";
        if (quality >= 0.7f) return "Good quality";
        if (quality >= 0.6f) return "Decent quality";
        return "Acceptable quality";
    }

    private String getAngleDescription(String angle) {
        switch (angle) {
            case "frontal": return "frontal view";
            case "left_profile": return "left profile";
            case "right_profile": return "right profile";
            case "slight_left": return "slight left angle";
            case "slight_right": return "slight right angle";
            default: return "angle";
        }
    }

    private String generateProgressMessage() {
        int remaining = Math.max(0, MIN_CAPTURES - capturedFaces.size());
        int highQualityNeeded = Math.max(0, TARGET_HIGH_QUALITY - highQualityCount);

        if (remaining > 0) {
            if (highQualityNeeded > 0) {
                return String.format("Need %d more shots (%d high-quality preferred). Keep looking at glasses.",
                        remaining, highQualityNeeded);
            } else {
                return String.format("Need %d more shots. Great quality so far!", remaining);
            }
        } else {
            Set<String> missingAngles = new HashSet<>(requiredAngles);
            capturedFaces.forEach(face -> missingAngles.remove(face.faceAngle));

            if (!missingAngles.isEmpty()) {
                return "Getting shots from different angles for better recognition...";
            } else {
                return "Excellent coverage! Capturing additional shots for best accuracy...";
            }
        }
    }
    private boolean shouldCompleteCapture() {
        if (capturedFaces.size() < 2) {
            return false;
        }

        if (capturedFaces.size() >= MIN_CAPTURES) {
            Log.d(TAG, "Completing capture: reached minimum captures");
            return true;
        }

        long totalTime = System.currentTimeMillis() - captureStartTime;
        if (totalTime > 15000 && capturedFaces.size() >= 2) {
            Log.d(TAG, "Completing: timeout with minimum images");
            return true;
        }

        return false;
    }

    private boolean hasMinimumAngleCoverage() {
        return capturedFaces.size() >= 2;
    }

    private void completeCapture() {
        isCapturing = false;

        capturedFaces.sort((a, b) -> Float.compare(b.qualityScore, a.qualityScore));

        Log.d(TAG, String.format(
                "Capture completed for %s: %d photos, %d high-quality, angles: %s",
                personName, capturedFaces.size(), highQualityCount,
                getUniqueAngles().toString()
        ));

        if (callback != null) {
            callback.onCaptureCompleted(personName, capturedFaces);
        }
    }

    private Set<String> getUniqueAngles() {
        Set<String> angles = new HashSet<>();
        capturedFaces.forEach(face -> angles.add(face.faceAngle));
        return angles;
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

    public int getHighQualityCount() {
        return highQualityCount;
    }

    public CaptureStatistics getStatistics() {
        return new CaptureStatistics(
                capturedFaces.size(),
                highQualityCount,
                getUniqueAngles().size(),
                capturedFaces.isEmpty() ? 0f :
                        (float) capturedFaces.stream()
                                .mapToDouble(face -> face.qualityScore)
                                .average().orElse(0.0),
                emergencyMode,
                currentQualityThreshold
        );
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

        public final FaceQualityAnalyzer.QualityMetrics qualityMetrics;
        public final float[] headPose;
        public final long timestamp;

        public CapturedFace(Bitmap bitmap, String faceAngle, String facePosition, float qualityScore, FaceQualityAnalyzer.QualityMetrics qualityMetrics, float[] headPose, long timestamp) {
            this.bitmap = bitmap;
            this.faceAngle = faceAngle;
            this.facePosition = facePosition;
            this.qualityScore = qualityScore;
            this.qualityMetrics = qualityMetrics;
            this.headPose = headPose;
            this.timestamp = timestamp;
        }

        public Map<String, Object> getMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("angle", faceAngle);
        metadata.put("position", facePosition);
        metadata.put("quality_score", qualityScore);
        metadata.put("face_size_score", qualityMetrics.faceSizeScore);
        metadata.put("pose_score", qualityMetrics.poseScore);
        metadata.put("eye_openness_score", qualityMetrics.eyeOpennessScore);
        metadata.put("brightness_score", qualityMetrics.brightnessScore);
        metadata.put("sharpness_score", qualityMetrics.sharpnessScore);
        metadata.put("landmark_score", qualityMetrics.landmarkScore);
        metadata.put("face_size_ratio", qualityMetrics.faceSizeRatio);
        metadata.put("head_pose_pitch", headPose[0]);
        metadata.put("head_pose_yaw", headPose[1]);
        metadata.put("head_pose_roll", headPose[2]);
        metadata.put("timestamp", timestamp);
        metadata.put("image_width", bitmap.getWidth());
        metadata.put("image_height", bitmap.getHeight());
        return metadata;
    }
}

public static class CaptureStatistics {
    public final int totalCaptures;
    public final int highQualityCaptures;
    public final int uniqueAngles;
    public final float averageQuality;
    public final boolean emergencyModeUsed;
    public final float finalQualityThreshold;

    public CaptureStatistics(int totalCaptures, int highQualityCaptures, int uniqueAngles,
                             float averageQuality, boolean emergencyModeUsed, float finalQualityThreshold) {
        this.totalCaptures = totalCaptures;
        this.highQualityCaptures = highQualityCaptures;
        this.uniqueAngles = uniqueAngles;
        this.averageQuality = averageQuality;
        this.emergencyModeUsed = emergencyModeUsed;
        this.finalQualityThreshold = finalQualityThreshold;
    }
}
public interface CaptureProgressCallback {
    void onCaptureStarted(String personName);
    void onRealTimeFeedback(String feedback, float qualityScore);
    void onTechnicalFeedback(String technicalFeedback, FaceQualityAnalyzer.QualityMetrics metrics);
    void onSuccessfulCapture(int captureNumber, String message);
    void onProgressUpdate(int currentCount, int targetCount, String progressMessage);
    void onCaptureCompleted(String personName, List<CapturedFace> capturedFaces);
    void onCaptureStopped(String reason);
    void onError(String error);
}
}
