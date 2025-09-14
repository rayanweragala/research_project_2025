package com.research.blindassistant;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.nfc.Tag;
import android.os.Looper;
import android.util.Log;
import android.os.Handler;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.face.*;

import java.util.List;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;


public class FaceQualityAnalyzer {
    private static final String TAG = "FaceQualityAnalyzer";

    private ExecutorService executorService;
    private Handler mainHandler;
    private Random random;
    private static final float MIN_FACE_SIZE_RATIO=0.20f;
    private static final float MAX_FACE_SIZE_RATIO=0.85f;
    private static final float OPTIMAL_FACE_SIZE_RATIO=0.40f;
    private static final float MIN_BRIGHTNESS = 60f;
    private static final float MAX_BRIGHTNESS = 220f;
    private static final float OPTIMAL_BRIGHTNESS = 128f;
    private static final float MIN_SHARPNESS = 0.4f;
    private static final float MAX_HEAD_ROTATION_YAW = 25f;
    private static final float MAX_HEAD_ROTATION_PITCH = 20f;
    private static final float MAX_HEAD_ROTATION_ROLL = 15f;
    private static final float MIN_QUALITY_SCORE = 0.6f;
    private static final int MIN_FACE_PIXELS = 100 * 100;
    private static final float EYE_OPENNESS_THRESHOLD = 0.3f;
    private static final float SMILE_THRESHOLD = 0.1f;
    private static final float MAX_BLUR_VARIANCE = 100f;

    private FaceDetector faceDetector;

    public FaceQualityAnalyzer() {
        executorService = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());
        FaceDetectorOptions options = new FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_ALL)
                .setMinFaceSize(0.15f)
                .enableTracking()
                .build();
        faceDetector = FaceDetection.getClient(options);
    }

    public void analyzeFaceQuality(Bitmap frame, QualityAnalysisCallback callback) {
        if (frame == null || callback == null) {
            return;
        }
        executorService.submit(() -> {
            performAnalysis(frame, callback);
        });
    }

    private void performAnalysis(Bitmap frame,QualityAnalysisCallback callback) {
        try {
            InputImage image = InputImage.fromBitmap(frame, 0);

            faceDetector.process(image)
                    .addOnSuccessListener(faces -> {
                        FaceQualityResult result;
                        if (faces.isEmpty()) {
                            result = createNoFaceResult();
                        } else {
                            Face bestFace = findBestFace(faces, frame.getWidth(), frame.getHeight());
                            result = analyzeFaceQuality(frame, bestFace);
                        }
                        mainHandler.post(() -> callback.onAnalysisComplete(result));
                    })
                    .addOnFailureListener(e -> {
                        Log.e(TAG, "Face detection failed", e);
                        FaceQualityResult errorResult = createErrorResult("Face detection failed: " + e.getMessage());
                        mainHandler.post(() -> callback.onAnalysisComplete(errorResult));
                    });

        } catch (Exception e) {
            Log.e(TAG, "Error in quality analysis", e);
            FaceQualityResult errorResult = createErrorResult("Analysis error: " + e.getMessage());
            mainHandler.post(() -> callback.onAnalysisComplete(errorResult));
        }
    }
 private Face findBestFace(List<Face> faces,int imageWidth,int imageHeight){
        Face bestFace = null;
        float bestScore = 0f;

        for(Face face:faces){
            Rect bounds = face.getBoundingBox();
            float faceArea = bounds.width() * bounds.height();
            float imageArea = imageHeight * imageWidth;
            float sizeScore = imageArea / faceArea;

            float centerX = imageWidth / 2f;
            float centerY = imageHeight / 2f;
            float faceCenterX = bounds.centerX();
            float faceCenterY = bounds.centerY();
            float maxDistance = (float) Math.sqrt(centerX * centerX + centerY * centerY);
            float distance = (float) Math.sqrt(
                    Math.pow(faceCenterX - centerX, 2) + Math.pow(faceCenterY - centerY, 2)
            );
            float positionScore = 1f - (distance / maxDistance);
            float totalScore = sizeScore * 0.7f + positionScore * 0.3f;
            if(totalScore > bestScore){
                bestScore = totalScore;
                bestFace = face;
            }
        }
        return bestFace;
 }

 private FaceQualityResult analyzeFaceQuality(Bitmap frame,Face face){
    QualityMetrics metrics = new QualityMetrics();
    Rect bounds = face.getBoundingBox();
    float facePixels = bounds.width() * bounds.height();
    float imagePixels = frame.getWidth() * frame.getHeight();
    float faceSizeRatio = facePixels / imagePixels;

     metrics.faceSizeScore = calculateFaceSizeScore(faceSizeRatio);
    metrics.faceSizeRatio = faceSizeRatio;

    Float rotY = face.getHeadEulerAngleY();
    Float rotX = face.getHeadEulerAngleX();
    Float rotZ = face.getHeadEulerAngleZ();

    metrics.poseScore = calculatePoseScore(rotX,rotY,rotZ);
    metrics.headPose = new float[]{
            rotX != null ? rotX: 0f,
            rotY != null ? rotY: 0f,
            rotZ != null ? rotZ: 0f
    };

     Float leftEyeOpen = face.getLeftEyeOpenProbability();
     Float rightEyeOpen = face.getRightEyeOpenProbability();
     metrics.eyeOpennessScore = calculateEyeOpennessScore(leftEyeOpen, rightEyeOpen);
     metrics.brightnessScore = calculateBrightnessScore(frame, bounds);
     metrics.sharpnessScore = calculateSharpnessScore(frame, bounds);
     metrics.landmarkScore = calculateLandmarkScore(face);
     float overallQuality = calculateOverallQuality(metrics);

     String feedback = generateDetailedFeedback(metrics, overallQuality);
     String technicalFeedback = generateTechnicalFeedback(metrics);

     boolean isGoodQuality = overallQuality >= MIN_QUALITY_SCORE &&
             metrics.faceSizeScore > 0.6f &&
             metrics.poseScore > 0.7f &&
             metrics.eyeOpennessScore > 0.6f;

     return new FaceQualityResult(
             isGoodQuality,
             overallQuality,
             feedback,
             technicalFeedback,
             getPoseDescription(metrics.headPose),
             getFacePosition(bounds, frame.getWidth(), frame.getHeight()),
             metrics,
             extractFaceForProcessing(frame, face)
     );
 }

 private float calculateFaceSizeScore(float faceSizeRatio){
        if(faceSizeRatio < MIN_FACE_SIZE_RATIO || faceSizeRatio > MAX_FACE_SIZE_RATIO){
            return 0f;
        }

        float distance = Math.abs(faceSizeRatio - OPTIMAL_FACE_SIZE_RATIO);
        float maxDistance = Math.max(OPTIMAL_FACE_SIZE_RATIO - MIN_FACE_SIZE_RATIO,MAX_FACE_SIZE_RATIO - OPTIMAL_FACE_SIZE_RATIO);

        return Math.max(0f,1f - distance / maxDistance);
 }

    private float calculatePoseScore(Float rotX, Float rotY, Float rotZ) {
        float pitch = Math.abs(rotX != null ? rotX : 0f);
        float yaw = Math.abs(rotY != null ? rotY : 0f);
        float roll = Math.abs(rotZ != null ? rotZ : 0f);

        float pitchScore = Math.max(0f, 1f - (pitch / MAX_HEAD_ROTATION_PITCH));
        float yawScore = Math.max(0f, 1f - (yaw / MAX_HEAD_ROTATION_YAW));
        float rollScore = Math.max(0f, 1f - (roll / MAX_HEAD_ROTATION_ROLL));

        return (pitchScore + yawScore + rollScore) / 3f;
    }

    private float calculateEyeOpennessScore(Float leftEye, Float rightEye) {
        if (leftEye == null || rightEye == null) return 0.5f;

        float avgEyeOpenness = (leftEye + rightEye) / 2f;
        return avgEyeOpenness > EYE_OPENNESS_THRESHOLD ? 1f : avgEyeOpenness / EYE_OPENNESS_THRESHOLD;
    }

    private float calculateBrightnessScore(Bitmap bitmap, Rect faceRegion) {
        float avgBrightness = calculateRegionBrightness(bitmap, faceRegion);

        if (avgBrightness < MIN_BRIGHTNESS || avgBrightness > MAX_BRIGHTNESS) {
            return 0f;
        }

        float distance = Math.abs(avgBrightness - OPTIMAL_BRIGHTNESS);
        float maxDistance = Math.max(OPTIMAL_BRIGHTNESS - MIN_BRIGHTNESS,
                MAX_BRIGHTNESS - OPTIMAL_BRIGHTNESS);
        return Math.max(0f, 1f - (distance / maxDistance));
    }

    private float calculateRegionBrightness(Bitmap bitmap, Rect region) {
        int startX = Math.max(0, region.left);
        int startY = Math.max(0, region.top);
        int endX = Math.min(bitmap.getWidth(), region.right);
        int endY = Math.min(bitmap.getHeight(), region.bottom);

        long totalBrightness = 0;
        int pixelCount = 0;

        for (int x = startX; x < endX; x += 5) {
            for (int y = startY; y < endY; y += 5) {
                int pixel = bitmap.getPixel(x, y);
                int r = (pixel >> 16) & 0xff;
                int g = (pixel >> 8) & 0xff;
                int b = pixel & 0xff;

                int brightness = (int) (0.299 * r + 0.587 * g + 0.114 * b);
                totalBrightness += brightness;
                pixelCount++;
            }
        }

        return pixelCount > 0 ? (float) totalBrightness / pixelCount : 0f;
    }

    private float calculateSharpnessScore(Bitmap bitmap, Rect faceRegion) {
        float variance = calculateLaplacianVariance(bitmap,faceRegion);
        return Math.min(1f,variance / MAX_BLUR_VARIANCE);
    }

    private float calculateLaplacianVariance(Bitmap bitmap, Rect region) {
        int startX = Math.max(1, region.left);
        int startY = Math.max(1, region.top);
        int endX = Math.min(bitmap.getWidth() - 1, region.right);
        int endY = Math.min(bitmap.getHeight() - 1, region.bottom);

        double sum = 0;
        double sumSquared = 0;
        int count = 0;

        for (int x = startX; x < endX; x++) {
            for (int y = startY; y < endY; y++) {
                int center = getGrayValue(bitmap.getPixel(x, y));
                int left = getGrayValue(bitmap.getPixel(x-1, y));
                int right = getGrayValue(bitmap.getPixel(x+1, y));
                int top = getGrayValue(bitmap.getPixel(x, y-1));
                int bottom = getGrayValue(bitmap.getPixel(x, y+1));

                double laplacian = Math.abs(-4 * center + left + right + top + bottom);
                sum += laplacian;
                sumSquared += laplacian * laplacian;
                count++;
            }
        }

        if (count == 0) return 0f;

        double mean = sum / count;
        double variance = (sumSquared / count) - (mean * mean);
        return (float) Math.max(0, variance);
    }

    private int getGrayValue(int pixel) {
        int r = (pixel >> 16) & 0xff;
        int g = (pixel >> 8) & 0xff;
        int b = pixel & 0xff;
        return (int) (0.299 * r + 0.587 * g + 0.114 * b);
    }

    private float calculateLandmarkScore(Face face) {
        int landmarkCount = 0;

        if (face.getLandmark(FaceLandmark.LEFT_EYE) != null) landmarkCount++;
        if (face.getLandmark(FaceLandmark.RIGHT_EYE) != null) landmarkCount++;
        if (face.getLandmark(FaceLandmark.NOSE_BASE) != null) landmarkCount++;
        if (face.getLandmark(FaceLandmark.MOUTH_LEFT) != null) landmarkCount++;
        if (face.getLandmark(FaceLandmark.MOUTH_RIGHT) != null) landmarkCount++;

        return (float) landmarkCount / 5f;
    }

    private float calculateOverallQuality(QualityMetrics metrics) {
        return metrics.faceSizeScore * 0.25f +
                metrics.poseScore * 0.25f +
                metrics.eyeOpennessScore * 0.15f +
                metrics.brightnessScore * 0.15f +
                metrics.sharpnessScore * 0.15f +
                metrics.landmarkScore * 0.05f;
    }

    private Bitmap extractFaceForProcessing(Bitmap original, Face face) {
        Rect bounds = face.getBoundingBox();

        int expansion = (int) (Math.min(bounds.width(), bounds.height()) * 0.2f);
        Rect expandedBounds = new Rect(
                Math.max(0, bounds.left - expansion),
                Math.max(0, bounds.top - expansion),
                Math.min(original.getWidth(), bounds.right + expansion),
                Math.min(original.getHeight(), bounds.bottom + expansion)
        );

        try {
            return Bitmap.createBitmap(original,
                    expandedBounds.left, expandedBounds.top,
                    expandedBounds.width(), expandedBounds.height());
        } catch (Exception e) {
            Log.e(TAG, "Error extracting face region", e);
            return original;
        }
    }

    private String generateDetailedFeedback(QualityMetrics metrics, float overallQuality) {
        if (overallQuality >= 0.8f) {
            return "Excellent quality! Perfect for recognition training.";
        } else if (overallQuality >= 0.6f) {
            return "Good quality. This will work well for training.";
        } else {
            if (metrics.faceSizeScore < 0.5f) {
                if (metrics.faceSizeRatio < MIN_FACE_SIZE_RATIO) {
                    return "Face too small - move closer to camera";
                } else {
                    return "Face too large - step back slightly";
                }
            } else if (metrics.poseScore < 0.5f) {
                return "Please look directly at the camera";
            } else if (metrics.brightnessScore < 0.5f) {
                return "Lighting needs adjustment - move to better lit area";
            } else if (metrics.sharpnessScore < 0.5f) {
                return "Image too blurry - hold steady and ensure good focus";
            } else if (metrics.eyeOpennessScore < 0.5f) {
                return "Please keep eyes open and look at camera";
            }
            return "Adjust position and lighting for better quality";
        }
    }

    private String generateTechnicalFeedback(QualityMetrics metrics) {
        return String.format("Size:%.2f Pose:%.2f Eyes:%.2f Bright:%.2f Sharp:%.2f Land:%.2f",
                metrics.faceSizeScore, metrics.poseScore, metrics.eyeOpennessScore,
                metrics.brightnessScore, metrics.sharpnessScore, metrics.landmarkScore);
    }

    private String getPoseDescription(float[] pose) {
        float pitch = Math.abs(pose[0]);
        float yaw = Math.abs(pose[1]);
        float roll = Math.abs(pose[2]);

        if (yaw < 10 && pitch < 10 && roll < 10) {
            return "frontal";
        } else if (yaw > 15) {
            return pose[1] > 0 ? "right_profile" : "left_profile";
        } else if (yaw > 5) {
            return pose[1] > 0 ? "slight_right" : "slight_left";
        } else {
            return "frontal";
        }
    }

    private String getFacePosition(Rect bounds, int imageWidth, int imageHeight) {
        float centerX = bounds.centerX() / (float) imageWidth;
        float centerY = bounds.centerY() / (float) imageHeight;
        return String.format("%.3f,%.3f", centerX, centerY);
    }

    private FaceQualityResult createNoFaceResult() {
        return new FaceQualityResult(
                false, 0.0f, "No face detected in image",
                "No face detected", "unknown", "0.5,0.5",
                new QualityMetrics(), null
        );
    }

    private FaceQualityResult createErrorResult(String error) {
        return new FaceQualityResult(
                false, 0.0f, error, error, "unknown", "0.5,0.5",
                new QualityMetrics(), null
        );
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
        public final String technicalFeedback;
        public final String faceAngle;
        public final String facePosition;
        public final QualityMetrics metrics;
        public final Bitmap processedFace;

        public FaceQualityResult(boolean isGoodQuality, float qualityScore, String feedback, String technicalFeedback, String faceAngle, String facePosition, QualityMetrics metrics, Bitmap processedFace) {
            this.isGoodQuality = isGoodQuality;
            this.qualityScore = qualityScore;
            this.feedback = feedback;
            this.technicalFeedback = technicalFeedback;
            this.faceAngle = faceAngle;
            this.facePosition = facePosition;
            this.metrics = metrics;
            this.processedFace = processedFace;
        }
    }

    public static class QualityMetrics {
        public float faceSizeScore = 0f;
        public float poseScore = 0f;
        public float eyeOpennessScore = 0f;
        public float brightnessScore = 0f;
        public float sharpnessScore = 0f;
        public float landmarkScore = 0f;
        public float faceSizeRatio = 0f;
        public float[] headPose = new float[]{0f, 0f, 0f};
    }


    public interface QualityAnalysisCallback {
        void onAnalysisComplete(FaceQualityResult result);
    }
}
