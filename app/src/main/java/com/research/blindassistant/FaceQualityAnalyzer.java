package com.research.blindassistant;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.nfc.Tag;
import android.util.Log;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.face.Face;
import com.google.mlkit.vision.face.FaceDetection;
import com.google.mlkit.vision.face.FaceDetector;
import com.google.mlkit.vision.face.FaceDetectorOptions;

import java.util.List;

public class FaceQualityAnalyzer {
    private static final String TAG = "FaceQualityAnalyzer";

    private static final float MIN_FACE_SIZE_RATIO=0.15f;
    private static final float MAX_FACE_SIZE_RATIO=0.8f;
    private static final float MIN_BRIGHTNESS = 80f;
    private static final float MAX_BRIGHTNESS = 200f;
    private static final float MIN_SHARPNESS = 0.3f;
    private static final float MAX_HEAD_ROTATION = 30f;

    private FaceDetector faceDetector;

    public FaceQualityAnalyzer(){
        FaceDetectorOptions options = new FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_ALL)
                .setMinFaceSize(0.1f)
                .enableTracking()
                .build();

        faceDetector = FaceDetection.getClient(options);
    }

    private void analyzeFaceQuality(Bitmap bitmap,FaceQualityCallback callBack){
        if(bitmap == null){
            callBack.onQualityResult(new FaceQualityResult(false,0f,"No image provided"));
            return;
        }

        InputImage image = InputImage.fromBitmap(bitmap,0);
        faceDetector.process(image)
                .addOnSuccessListener(faces -> {
                    FaceQualityResult result = evaluateFaces(faces,bitmap);
                    callBack.onQualityResult(result);
                })
                .addOnFailureListener(e->{
                    Log.e(TAG,"face detection failed",e);
                    callBack.onQualityResult(new FaceQualityResult(false, 0f, "Face detection failed"));
                });
    }

    private FaceQualityResult evaluateFaces(List<Face> faces,Bitmap bitmap){
        if(faces.isEmpty()){
            return new FaceQualityResult(false,0f,"no faces detected");
        }

        if(faces.size()>1){
            return new FaceQualityResult(false,0f,"Multiple faces detected - please ensure only one person is visible");
        }

        Face face = faces.get(0);
        float qualityScore =0f;
        StringBuilder issues = new StringBuilder();

        float faceSizeScore = analyzeFaceSize(face,bitmap,issues);
        qualityScore += faceSizeScore * 0.25f;

        float positionScore = analyzeFacePosition(face,bitmap,issues);
        qualityScore += positionScore * 0.20f;

        float poseScore = analyzeHeadPose(face, issues);
        qualityScore += poseScore * 0.20f;

        float brightnessScore = analyzeBrightness(bitmap, face, issues);
        qualityScore += brightnessScore * 0.15f;

        float sharpnessScore = analyzeSharpness(bitmap, face, issues);
        qualityScore += sharpnessScore * 0.15f;

        float eyeScore = analyzeEyes(face, issues);
        qualityScore += eyeScore * 0.05f;

        boolean isGoodQuality = qualityScore >= 0.7f;

        String feedback = isGoodQuality ? "Excellent quality" : issues.toString();

        return new FaceQualityResult(isGoodQuality, qualityScore, feedback,
                extractFaceAngle(face), extractFacePosition(face, bitmap));
    }

    private float analyzeFaceSize(Face face, Bitmap bitmap, StringBuilder issues) {
        Rect bounds = face.getBoundingBox();
        float faceArea = bounds.width() * bounds.height();
        float imageArea = bitmap.getWidth() * bitmap.getHeight();
        float faceRatio = faceArea / imageArea;

        if (faceRatio < MIN_FACE_SIZE_RATIO) {
            issues.append("Person is too far away. ");
            return Math.max(0f, faceRatio / MIN_FACE_SIZE_RATIO);
        } else if (faceRatio > MAX_FACE_SIZE_RATIO) {
            issues.append("Person is too close. ");
            return Math.max(0f, (1f - faceRatio) / (1f - MAX_FACE_SIZE_RATIO));
        }

        return 1.0f;
    }

    private float analyzeFacePosition(Face face, Bitmap bitmap, StringBuilder issues) {
        Rect bounds = face.getBoundingBox();
        float centerX = bounds.centerX();
        float centerY = bounds.centerY();
        float imageCenterX = bitmap.getWidth() / 2f;
        float imageCenterY = bitmap.getHeight() / 2f;

        float horizontalOffset = Math.abs(centerX - imageCenterX) / imageCenterX;
        float verticalOffset = Math.abs(centerY - imageCenterY) / imageCenterY;

        if (horizontalOffset > 0.3f) {
            issues.append("Please center the person horizontally. ");
        }
        if (verticalOffset > 0.3f) {
            issues.append("Please center the person vertically. ");
        }

        return Math.max(0f, 1f - (horizontalOffset + verticalOffset) / 2f);
    }

    private float analyzeHeadPose(Face face, StringBuilder issues) {
        float rotY = Math.abs(face.getHeadEulerAngleY());
        float rotZ = Math.abs(face.getHeadEulerAngleZ());
        float rotX = Math.abs(face.getHeadEulerAngleX());

        if (rotY > MAX_HEAD_ROTATION) {
            issues.append("Please face the camera more directly. ");
        }
        if (rotZ > MAX_HEAD_ROTATION) {
            issues.append("Please keep head level. ");
        }
        if (rotX > MAX_HEAD_ROTATION) {
            issues.append("Please look straight ahead. ");
        }

        float maxRotation = Math.max(rotY, Math.max(rotZ, rotX));
        return Math.max(0f, 1f - maxRotation / MAX_HEAD_ROTATION);
    }

    private float analyzeBrightness(Bitmap bitmap, Face face, StringBuilder issues) {
        Rect bounds = face.getBoundingBox();

        int sampleCount = 0;
        long totalBrightness = 0;

        int step = 10;
        for (int x = bounds.left; x < bounds.right; x += step) {
            for (int y = bounds.top; y < bounds.bottom; y += step) {
                if (x >= 0 && x < bitmap.getWidth() && y >= 0 && y < bitmap.getHeight()) {
                    int pixel = bitmap.getPixel(x, y);
                    int brightness = (int) (0.299 * ((pixel >> 16) & 0xFF) +
                            0.587 * ((pixel >> 8) & 0xFF) +
                            0.114 * (pixel & 0xFF));
                    totalBrightness += brightness;
                    sampleCount++;
                }
            }
        }

        if (sampleCount == 0) return 0f;

        float avgBrightness = totalBrightness / (float) sampleCount;

        if (avgBrightness < MIN_BRIGHTNESS) {
            issues.append("Too dark - please move to better lighting. ");
            return avgBrightness / MIN_BRIGHTNESS;
        } else if (avgBrightness > MAX_BRIGHTNESS) {
            issues.append("Too bright - please avoid direct light. ");
            return Math.max(0f, (255f - avgBrightness) / (255f - MAX_BRIGHTNESS));
        }

        return 1.0f;
    }

    private float analyzeSharpness(Bitmap bitmap, Face face, StringBuilder issues) {
        Rect bounds = face.getBoundingBox();

        int totalVariance = 0;
        int sampleCount = 0;

        for (int x = bounds.left + 1; x < bounds.right - 1; x += 5) {
            for (int y = bounds.top + 1; y < bounds.bottom - 1; y += 5) {
                if (x >= 1 && x < bitmap.getWidth() - 1 && y >= 1 && y < bitmap.getHeight() - 1) {
                    int center = getGrayValue(bitmap.getPixel(x, y));
                    int left = getGrayValue(bitmap.getPixel(x - 1, y));
                    int right = getGrayValue(bitmap.getPixel(x + 1, y));
                    int top = getGrayValue(bitmap.getPixel(x, y - 1));
                    int bottom = getGrayValue(bitmap.getPixel(x, y + 1));

                    int laplacian = Math.abs(4 * center - left - right - top - bottom);
                    totalVariance += laplacian * laplacian;
                    sampleCount++;
                }
            }
        }

        if (sampleCount == 0) return 0f;

        float variance = totalVariance / (float) sampleCount;
        float normalizedSharpness = Math.min(1f, variance / 10000f);

        if (normalizedSharpness < MIN_SHARPNESS) {
            issues.append("Image is blurry - please hold steady. ");
            return normalizedSharpness / MIN_SHARPNESS;
        }

        return 1.0f;
    }

    private int getGrayValue(int pixel) {
        return (int) (0.299 * ((pixel >> 16) & 0xFF) +
                0.587 * ((pixel >> 8) & 0xFF) +
                0.114 * (pixel & 0xFF));
    }

    private float analyzeEyes(Face face, StringBuilder issues) {
        Float leftEyeOpen = face.getLeftEyeOpenProbability();
        Float rightEyeOpen = face.getRightEyeOpenProbability();

        if (leftEyeOpen != null && rightEyeOpen != null) {
            float eyeScore = (leftEyeOpen + rightEyeOpen) / 2f;
            if (eyeScore < 0.5f) {
                issues.append("Please keep eyes open. ");
            }
            return eyeScore;
        }

        return 1.0f;
    }

    private String extractFaceAngle(Face face) {
        float rotY = face.getHeadEulerAngleY();
        if (Math.abs(rotY) < 10) return "front";
        else if (rotY > 10) return "left_profile";
        else return "right_profile";
    }

    private String extractFacePosition(Face face, Bitmap bitmap) {
        Rect bounds = face.getBoundingBox();
        float centerX = bounds.centerX() / (float) bitmap.getWidth();
        float centerY = bounds.centerY() / (float) bitmap.getHeight();

        return String.format("%.2f,%.2f", centerX, centerY);
    }

    public void cleanup() {
        if (faceDetector != null) {
            faceDetector.close();
        }
    }

    public interface FaceQualityCallback {
        void onQualityResult(FaceQualityResult result);
    }

    public static class FaceQualityResult {
        public final boolean isGoodQuality;
        public final float qualityScore;
        public final String feedback;
        public final String faceAngle;
        public final String facePosition;

        public FaceQualityResult(boolean isGoodQuality, float qualityScore, String feedback) {
            this(isGoodQuality, qualityScore, feedback, "unknown", "0.5,0.5");
        }

        public FaceQualityResult(boolean isGoodQuality, float qualityScore, String feedback,
                                 String faceAngle, String facePosition) {
            this.isGoodQuality = isGoodQuality;
            this.qualityScore = qualityScore;
            this.feedback = feedback;
            this.faceAngle = faceAngle;
            this.facePosition = facePosition;
        }
    }
}
