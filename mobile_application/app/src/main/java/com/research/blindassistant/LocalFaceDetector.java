package com.research.blindassistant;

import android.graphics.*;
import android.media.FaceDetector;
import android.util.Log;

import java.util.ArrayList;
import java.util.List;

public class LocalFaceDetector {

    private static final String TAG = "LocalFaceDetector";
    private static final int MAX_FACES = 10;
    private static final float MIN_FACE_SIZE = 20.0f;
    private static final float MIN_CONFIDENCE = 0.4f;

    private FaceDetector faceDetector;
    private DetectionStats stats;
    private Paint debugPaint;

    public LocalFaceDetector() {
        stats = new DetectionStats();
        setupDebugPaint();
    }

    private void setupDebugPaint() {
        debugPaint = new Paint();
        debugPaint.setColor(Color.GREEN);
        debugPaint.setStyle(Paint.Style.STROKE);
        debugPaint.setStrokeWidth(3.0f);
        debugPaint.setAntiAlias(true);
    }

    public FaceDetectionResult detectFaces(Bitmap bitmap) {
        if (bitmap == null || bitmap.isRecycled()) {
            return new FaceDetectionResult(false, "Invalid bitmap", 0.0f, 0);
        }

        long startTime = System.currentTimeMillis();

        try {
            Bitmap rgbBitmap = convertToRGB565(bitmap);
            if (rgbBitmap == null) {
                return new FaceDetectionResult(false, "Bitmap conversion failed", 0.0f, 0);
            }

            if (faceDetector == null) {
                faceDetector = new FaceDetector(rgbBitmap.getWidth(), rgbBitmap.getHeight(), MAX_FACES);
            }

            FaceDetector.Face[] faces = new FaceDetector.Face[MAX_FACES];
            int numFaces = faceDetector.findFaces(rgbBitmap, faces);

            long processingTime = System.currentTimeMillis() - startTime;
            stats.addProcessingTime(processingTime);

            if (numFaces > 0) {
                return processFaceDetectionResults(faces, numFaces, rgbBitmap.getWidth(), rgbBitmap.getHeight());
            } else {
                return new FaceDetectionResult(false, "No faces detected", 0.0f, 0);
            }

        } catch (Exception e) {
            Log.e(TAG, "Error during face detection", e);
            return new FaceDetectionResult(false, "Detection error: " + e.getMessage(), 0.0f, 0);
        }
    }

    private Bitmap convertToRGB565(Bitmap original) {
        try {
            if (original.getConfig() == Bitmap.Config.RGB_565) {
                return original;
            }

            Bitmap rgb565Bitmap = Bitmap.createBitmap(
                    original.getWidth(),
                    original.getHeight(),
                    Bitmap.Config.RGB_565
            );

            Canvas canvas = new Canvas(rgb565Bitmap);
            canvas.drawBitmap(original, 0, 0, null);

            return rgb565Bitmap;
        } catch (Exception e) {
            Log.e(TAG, "Error converting bitmap to RGB565", e);
            return null;
        }
    }

    private FaceDetectionResult processFaceDetectionResults(FaceDetector.Face[] faces, int numFaces, int width, int height) {
        List<DetectedFace> detectedFaces = new ArrayList<>();
        float bestConfidence = 0.0f;
        float totalConfidence = 0.0f;

        for (int i = 0; i < numFaces; i++) {
            FaceDetector.Face face = faces[i];
            if (face == null) continue;

            float confidence = face.confidence();
            if (confidence < MIN_CONFIDENCE) continue;

            PointF midPoint = new PointF();
            face.getMidPoint(midPoint);
            float eyeDistance = face.eyesDistance();

            float faceRadius = eyeDistance * 1.5f;
            if (faceRadius < MIN_FACE_SIZE) continue;

            Rect faceBounds = new Rect(
                    (int) (midPoint.x - faceRadius),
                    (int) (midPoint.y - faceRadius),
                    (int) (midPoint.x + faceRadius),
                    (int) (midPoint.y + faceRadius)
            );

            faceBounds.intersect(0, 0, width, height);

            DetectedFace detectedFace = new DetectedFace(faceBounds, confidence, eyeDistance);
            detectedFaces.add(detectedFace);

            totalConfidence += confidence;
            if (confidence > bestConfidence) {
                bestConfidence = confidence;
            }
        }

        if (detectedFaces.isEmpty()) {
            return new FaceDetectionResult(false, "No valid faces found", 0.0f, 0);
        }

        float qualityScore = calculateQualityScore(detectedFaces.get(0), width, height);

        String message = String.format("Found %d face%s",
                detectedFaces.size(),
                detectedFaces.size() == 1 ? "" : "s"
        );

        return new FaceDetectionResult(true, message, qualityScore, detectedFaces.size(), detectedFaces);
    }

    private float calculateQualityScore(DetectedFace face, int imageWidth, int imageHeight) {
        float score = face.confidence;

        float faceSize = face.bounds.width() * face.bounds.height();
        float imageSize = imageWidth * imageHeight;
        float sizeRatio = faceSize / imageSize;
        float sizeScore = Math.min(1.0f, sizeRatio * 10);

        float centerX = imageWidth / 2.0f;
        float centerY = imageHeight / 2.0f;
        float faceCenterX = face.bounds.centerX();
        float faceCenterY = face.bounds.centerY();

        float distanceFromCenter = (float) Math.sqrt(
                Math.pow(faceCenterX - centerX, 2) + Math.pow(faceCenterY - centerY, 2)
        );
        float maxDistance = (float) Math.sqrt(Math.pow(centerX, 2) + Math.pow(centerY, 2));
        float positionScore = 1.0f - (distanceFromCenter / maxDistance);

        return (score * 0.5f + sizeScore * 0.3f + positionScore * 0.2f);
    }

    public void resetStats() {
        stats.reset();
    }

    public DetectionStats getStats() {
        return stats;
    }

    public void release() {
        faceDetector = null;
        stats = null;
    }
    public static class FaceDetectionResult {
        private final boolean hasFaces;
        private final String message;
        private final float qualityScore;
        private final int faceCount;
        private final List<DetectedFace> faces;

        public FaceDetectionResult(boolean hasFaces, String message, float qualityScore, int faceCount) {
            this(hasFaces, message, qualityScore, faceCount, new ArrayList<>());
        }

        public FaceDetectionResult(boolean hasFaces, String message, float qualityScore, int faceCount, List<DetectedFace> faces) {
            this.hasFaces = hasFaces;
            this.message = message;
            this.qualityScore = qualityScore;
            this.faceCount = faceCount;
            this.faces = faces != null ? faces : new ArrayList<>();
        }

        public boolean hasFaces() { return hasFaces; }
        public String getMessage() { return message; }
        public float getQualityScore() { return qualityScore; }
        public int getFaceCount() { return faceCount; }
        public List<DetectedFace> getFaces() { return faces; }
    }

    public static class DetectedFace {
        public final Rect bounds;
        public final float confidence;
        public final float eyeDistance;

        public DetectedFace(Rect bounds, float confidence, float eyeDistance) {
            this.bounds = bounds;
            this.confidence = confidence;
            this.eyeDistance = eyeDistance;
        }
    }

    public static class DetectionStats {
        private long totalProcessingTime = 0;
        private int totalDetections = 0;
        private int successfulDetections = 0;

        public void addProcessingTime(long time) {
            totalProcessingTime += time;
            totalDetections++;
        }

        public void incrementSuccessfulDetections() {
            successfulDetections++;
        }

        public double getAvgProcessingTime() {
            return totalDetections > 0 ? (double) totalProcessingTime / totalDetections : 0.0;
        }

        public int getTotalDetections() { return totalDetections; }
        public int getSuccessfulDetections() { return successfulDetections; }
        public long getTotalProcessingTime() { return totalProcessingTime; }

        public void reset() {
            totalProcessingTime = 0;
            totalDetections = 0;
            successfulDetections = 0;
        }
    }
}
