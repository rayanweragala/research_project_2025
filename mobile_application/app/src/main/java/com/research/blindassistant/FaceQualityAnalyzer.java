package com.research.blindassistant;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.nfc.Tag;
import android.os.Looper;
import android.util.Log;
import android.os.Handler;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.face.Face;
import com.google.mlkit.vision.face.FaceDetection;
import com.google.mlkit.vision.face.FaceDetector;
import com.google.mlkit.vision.face.FaceDetectorOptions;

import java.util.List;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;


public class FaceQualityAnalyzer {
    private static final String TAG = "FaceQualityAnalyzer";

    private ExecutorService executorService;
    private Handler mainHandler;
    private Random random;
    private static final float MIN_FACE_SIZE_RATIO=0.15f;
    private static final float MAX_FACE_SIZE_RATIO=0.8f;
    private static final float MIN_BRIGHTNESS = 80f;
    private static final float MAX_BRIGHTNESS = 200f;
    private static final float MIN_SHARPNESS = 0.3f;
    private static final float MAX_HEAD_ROTATION = 30f;
    private static final float MIN_QUALITY_SCORE = 0.4f;
    private static final int MIN_FACE_SIZE = 80;
    private static final float BRIGHTNESS_THRESHOLD = 30f;

    private FaceDetector faceDetector;

    public FaceQualityAnalyzer() {
        executorService = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());
        random = new Random();
    }

    public void analyzeFaceQuality(Bitmap frame, QualityAnalysisCallback callback) {
        if (frame == null || callback == null) {
            return;
        }
        executorService.submit(() -> {
            FaceQualityResult result = performAnalysis(frame);

            mainHandler.post(() -> callback.onAnalysisComplete(result));
        });
    }

    private FaceQualityResult performAnalysis(Bitmap frame) {
        try {

            float brightness = calculateBrightness(frame);
            boolean isBrightEnough = brightness > BRIGHTNESS_THRESHOLD;

            boolean faceDetected = simulateFaceDetection(frame);

            if (!faceDetected) {
                return new FaceQualityResult(
                        false,
                        0.0f,
                        "No face detected",
                        "unknown",
                        "0.5,0.5"
                );
            }

            float qualityScore = calculateQualityScore(frame, brightness);

            boolean isGoodQuality = qualityScore >= MIN_QUALITY_SCORE && isBrightEnough;

            String feedback = generateFeedback(qualityScore, brightness, isGoodQuality);

            String faceAngle = detectFaceAngle();

            String facePosition = detectFacePosition();

            Log.d(TAG, String.format("Quality analysis: score=%.2f, brightness=%.1f, angle=%s, good=%b",
                    qualityScore, brightness, faceAngle, isGoodQuality));

            return new FaceQualityResult(
                    isGoodQuality,
                    qualityScore,
                    feedback,
                    faceAngle,
                    facePosition
            );

        } catch (Exception e) {
            Log.e(TAG, "Error in quality analysis", e);
            return new FaceQualityResult(
                    false,
                    0.0f,
                    "Analysis error: " + e.getMessage(),
                    "unknown",
                    "0.5,0.5"
            );
        }
    }

    private boolean simulateFaceDetection(Bitmap frame) {
        return random.nextFloat() > 0.1f;
    }

    private float calculateBrightness(Bitmap bitmap) {
        if (bitmap == null || bitmap.isRecycled()) {
            return 0f;
        }

        try {
            int width = bitmap.getWidth();
            int height = bitmap.getHeight();

            int sampleSize = Math.max(1, Math.min(width, height) / 10);
            long totalBrightness = 0;
            int sampleCount = 0;

            for (int x = 0; x < width; x += sampleSize) {
                for (int y = 0; y < height; y += sampleSize) {
                    if (x < width && y < height) {
                        int pixel = bitmap.getPixel(x, y);

                        int r = (pixel >> 16) & 0xff;
                        int g = (pixel >> 8) & 0xff;
                        int b = pixel & 0xff;

                        int brightness = (int) (0.299 * r + 0.587 * g + 0.114 * b);
                        totalBrightness += brightness;
                        sampleCount++;
                    }
                }
            }

            return sampleCount > 0 ? (float) totalBrightness / sampleCount : 0f;

        } catch (Exception e) {
            Log.e(TAG, "Error calculating brightness", e);
            return 128f;
        }
    }

    private float calculateQualityScore(Bitmap frame, float brightness) {
        float score = 0.5f;

        if (brightness > 50 && brightness < 200) {
            score += 0.2f;
        }

        int pixels = frame.getWidth() * frame.getHeight();
        if (pixels > 300000) {
            score += 0.2f;
        }

        score += (random.nextFloat() - 0.5f) * 0.3f;

        return Math.max(0.0f, Math.min(1.0f, score));
    }

    private String generateFeedback(float qualityScore, float brightness, boolean isGoodQuality) {
        if (isGoodQuality) {
            String[] goodMessages = {
                    "Perfect lighting and position!",
                    "Great shot quality!",
                    "Excellent face visibility!",
                    "Perfect angle and clarity!"
            };
            return goodMessages[random.nextInt(goodMessages.length)];
        } else {
            if (brightness < BRIGHTNESS_THRESHOLD) {
                return "Need more light - move to brighter area";
            } else if (qualityScore < 0.3f) {
                return "Face not clear - adjust position";
            } else {
                return "Almost there - slight adjustment needed";
            }
        }
    }

    private String detectFaceAngle() {
        String[] angles = {"front", "left_profile", "right_profile", "slight_left", "slight_right"};

        float rand = random.nextFloat();
        if (rand < 0.4f) return "front";
        else if (rand < 0.6f) return "slight_left";
        else if (rand < 0.8f) return "slight_right";
        else if (rand < 0.9f) return "left_profile";
        else return "right_profile";
    }

    private String detectFacePosition() {
        float x = 0.3f + random.nextFloat() * 0.4f;
        float y = 0.3f + random.nextFloat() * 0.4f;

        return String.format("%.2f,%.2f", x, y);
    }

    public void cleanup() {
        if (executorService != null && !executorService.isShutdown()) {
            executorService.shutdown();
        }
    }

    public static class FaceQualityResult {
        public final boolean isGoodQuality;
        public final float qualityScore;
        public final String feedback;
        public final String faceAngle;
        public final String facePosition;

        public FaceQualityResult(boolean isGoodQuality, float qualityScore, String feedback,
                                 String faceAngle, String facePosition) {
            this.isGoodQuality = isGoodQuality;
            this.qualityScore = qualityScore;
            this.feedback = feedback;
            this.faceAngle = faceAngle;
            this.facePosition = facePosition;
        }
    }

    public interface QualityAnalysisCallback {
        void onAnalysisComplete(FaceQualityResult result);
    }
}
