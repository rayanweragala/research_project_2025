package com.research.blindassistant;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Rect;
import android.hardware.camera2.*;
import android.hardware.camera2.params.MeteringRectangle;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;
import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * Enhanced camera manager specifically optimized for Sinhala OCR document capture
 * Integrates with the new SinhalaOCRActivity layout and provides optimized image processing
 */
public class OCRCameraManager {
    private static final String TAG = "OCRCameraManager";

    // Camera settings optimized for Sinhala text recognition
    private static final int IMAGE_WIDTH = 1920;
    private static final int IMAGE_HEIGHT = 1080;
    private static final int MAX_PREVIEW_WIDTH = 1920;
    private static final int MAX_PREVIEW_HEIGHT = 1080;

    private Context context;
    private Activity activity;
    private TextureView textureView;

    // Camera2 API components
    private CameraManager cameraManager;
    private CameraDevice cameraDevice;
    private CameraCaptureSession captureSession;
    private CaptureRequest.Builder previewRequestBuilder;
    private CaptureRequest previewRequest;
    private ImageReader imageReader;

    // Background thread handling
    private HandlerThread backgroundThread;
    private Handler backgroundHandler;

    // Camera properties
    private String cameraId;
    private Size imageDimension;
    private boolean flashSupported;
    private boolean autoFocusSupported;
    private boolean isCapturing = false;

    // Callbacks
    private OCRCameraCallback callback;

    public interface OCRCameraCallback {
        void onCameraReady();
        void onCameraError(String error);
        void onImageCaptured(Bitmap bitmap);
        void onPreviewFrame(Bitmap frame);
    }

    public OCRCameraManager(Activity activity, TextureView textureView) {
        this.activity = activity;
        this.context = activity.getApplicationContext();
        this.textureView = textureView;
        this.cameraManager = (CameraManager) context.getSystemService(Context.CAMERA_SERVICE);
    }

    public void setCallback(OCRCameraCallback callback) {
        this.callback = callback;
    }

    /**
     * Initialize and start camera for Sinhala OCR document capture
     */
    public void startCamera() {
        Log.d(TAG, "Starting OCR camera");
        startBackgroundThread();

        if (textureView.isAvailable()) {
            openCamera();
        } else {
            textureView.setSurfaceTextureListener(textureListener);
        }
    }

    /**
     * Stop camera and cleanup resources
     */
    public void stopCamera() {
        Log.d(TAG, "Stopping OCR camera");
        closeCamera();
        stopBackgroundThread();
    }

    /**
     * Capture a high-quality image optimized for Sinhala OCR processing
     */
    public void captureOCRImage() {
        if (cameraDevice == null) {
            Log.e(TAG, "Camera device is null, cannot capture image");
            if (callback != null) {
                callback.onCameraError("Camera not available for capture");
            }
            return;
        }

        if (isCapturing) {
            Log.w(TAG, "Already capturing image, ignoring request");
            return;
        }

        isCapturing = true;
        Log.d(TAG, "Starting OCR image capture");

        try {
            // Create capture request optimized for document text
            CaptureRequest.Builder captureBuilder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
            captureBuilder.addTarget(imageReader.getSurface());

            // Optimize settings specifically for Sinhala text capture
            setupCaptureRequestForSinhalaOCR(captureBuilder);

            // Capture the image
            CameraCaptureSession.CaptureCallback captureCallback = new CameraCaptureSession.CaptureCallback() {
                @Override
                public void onCaptureCompleted(@NonNull CameraCaptureSession session,
                                               @NonNull CaptureRequest request,
                                               @NonNull TotalCaptureResult result) {
                    Log.d(TAG, "Sinhala OCR image capture completed successfully");
                    isCapturing = false;
                }

                @Override
                public void onCaptureFailed(@NonNull CameraCaptureSession session,
                                            @NonNull CaptureRequest request,
                                            @NonNull CaptureFailure failure) {
                    Log.e(TAG, "Sinhala OCR image capture failed: " + failure.getReason());
                    isCapturing = false;
                    if (callback != null) {
                        callback.onCameraError("Image capture failed: " + failure.getReason());
                    }
                }
            };

            captureSession.capture(captureBuilder.build(), captureCallback, backgroundHandler);

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error capturing Sinhala OCR image", e);
            isCapturing = false;
            if (callback != null) {
                callback.onCameraError("Camera access error during capture: " + e.getMessage());
            }
        }
    }

    private void setupCaptureRequestForSinhalaOCR(CaptureRequest.Builder captureBuilder) {
        // Basic camera controls
        captureBuilder.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
        captureBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
        captureBuilder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON);

        // Enhanced sharpness and edge detection for Sinhala characters
        captureBuilder.set(CaptureRequest.EDGE_MODE, CaptureRequest.EDGE_MODE_HIGH_QUALITY);
        captureBuilder.set(CaptureRequest.NOISE_REDUCTION_MODE, CaptureRequest.NOISE_REDUCTION_MODE_HIGH_QUALITY);

        // Color correction for better text contrast
        captureBuilder.set(CaptureRequest.COLOR_CORRECTION_MODE, CaptureRequest.COLOR_CORRECTION_MODE_HIGH_QUALITY);

        // Stabilization for clearer text
        captureBuilder.set(CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE,
                CaptureRequest.LENS_OPTICAL_STABILIZATION_MODE_ON);

        // Use flash if available for better document illumination
        if (flashSupported) {
            captureBuilder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON_AUTO_FLASH);
        }

        // Set focus distance for optimal document reading range (if supported)
        captureBuilder.set(CaptureRequest.LENS_FOCUS_DISTANCE, 0.3f); // Close focus for documents

        Log.d(TAG, "Capture request configured for Sinhala OCR optimization");
    }

    private void openCamera() {
        try {
            // Find the best camera for Sinhala document capture
            cameraId = getBestCameraForOCR();
            if (cameraId == null) {
                if (callback != null) {
                    callback.onCameraError("No suitable camera found for Sinhala OCR");
                }
                return;
            }

            // Get camera characteristics
            CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(cameraId);
            StreamConfigurationMap map = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);

            if (map == null) {
                if (callback != null) {
                    callback.onCameraError("Camera configuration not available");
                }
                return;
            }

            // Check camera capabilities
            checkCameraCapabilities(characteristics);

            // Set optimal image size for Sinhala OCR
            imageDimension = getOptimalSizeForSinhalaOCR(map.getOutputSizes(ImageFormat.JPEG));
            Log.d(TAG, String.format("Selected image dimension: %dx%d",
                    imageDimension.getWidth(), imageDimension.getHeight()));

            // Setup image reader for capturing high-quality images
            imageReader = ImageReader.newInstance(imageDimension.getWidth(), imageDimension.getHeight(),
                    ImageFormat.JPEG, 1);
            imageReader.setOnImageAvailableListener(onImageAvailableListener, backgroundHandler);

            // Check permissions
            if (ActivityCompat.checkSelfPermission(context, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                if (callback != null) {
                    callback.onCameraError("Camera permission not granted");
                }
                return;
            }

            // Open camera
            cameraManager.openCamera(cameraId, stateCallback, backgroundHandler);

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error opening camera for Sinhala OCR", e);
            if (callback != null) {
                callback.onCameraError("Camera access error: " + e.getMessage());
            }
        }
    }

    private String getBestCameraForOCR() {
        try {
            String[] cameraIds = cameraManager.getCameraIdList();

            // Prefer back camera with highest resolution for document capture
            String bestCameraId = null;
            int maxResolution = 0;

            for (String id : cameraIds) {
                CameraCharacteristics characteristics = cameraManager.getCameraCharacteristics(id);
                Integer facing = characteristics.get(CameraCharacteristics.LENS_FACING);

                if (facing != null && facing == CameraCharacteristics.LENS_FACING_BACK) {
                    StreamConfigurationMap map = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
                    if (map != null && map.getOutputSizes(ImageFormat.JPEG) != null) {
                        Size[] sizes = map.getOutputSizes(ImageFormat.JPEG);
                        for (Size size : sizes) {
                            int resolution = size.getWidth() * size.getHeight();
                            if (resolution > maxResolution) {
                                maxResolution = resolution;
                                bestCameraId = id;
                            }
                        }
                    }
                }
            }

            // Fallback to any available camera
            if (bestCameraId == null && cameraIds.length > 0) {
                bestCameraId = cameraIds[0];
            }

            Log.d(TAG, String.format("Selected camera %s with max resolution %d", bestCameraId, maxResolution));
            return bestCameraId;

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error getting camera list", e);
            return null;
        }
    }

    private void checkCameraCapabilities(CameraCharacteristics characteristics) {
        // Check flash support
        Boolean flashAvailable = characteristics.get(CameraCharacteristics.FLASH_INFO_AVAILABLE);
        flashSupported = flashAvailable != null && flashAvailable;

        // Check autofocus support
        int[] afModes = characteristics.get(CameraCharacteristics.CONTROL_AF_AVAILABLE_MODES);
        autoFocusSupported = afModes != null && afModes.length > 1;

        // Log additional capabilities relevant for OCR
        float[] focalLengths = characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS);
        Float minFocusDistance = characteristics.get(CameraCharacteristics.LENS_INFO_MINIMUM_FOCUS_DISTANCE);

        Log.d(TAG, String.format("Camera capabilities - Flash: %s, AutoFocus: %s, MinFocus: %s",
                flashSupported, autoFocusSupported,
                minFocusDistance != null ? String.format("%.2fm", 1.0f / minFocusDistance) : "Unknown"));
    }

    private Size getOptimalSizeForSinhalaOCR(Size[] choices) {
        // Sort sizes by total pixels (descending)
        List<Size> sizeList = Arrays.asList(choices);
        Collections.sort(sizeList, new Comparator<Size>() {
            @Override
            public int compare(Size lhs, Size rhs) {
                return Integer.compare(rhs.getWidth() * rhs.getHeight(), lhs.getWidth() * lhs.getHeight());
            }
        });

        // Find the best size for Sinhala OCR (high resolution but not excessive)
        for (Size option : sizeList) {
            if (option.getWidth() <= MAX_PREVIEW_WIDTH && option.getHeight() <= MAX_PREVIEW_HEIGHT) {
                // Prefer 16:9 or 4:3 aspect ratio for documents
                float aspectRatio = (float) option.getWidth() / option.getHeight();
                if (aspectRatio >= 1.3f && aspectRatio <= 1.8f) {
                    Log.d(TAG, String.format("Selected optimal size: %dx%d (aspect: %.2f)",
                            option.getWidth(), option.getHeight(), aspectRatio));
                    return option;
                }
            }
        }

        // Fallback to largest available size within limits
        for (Size option : sizeList) {
            if (option.getWidth() <= MAX_PREVIEW_WIDTH && option.getHeight() <= MAX_PREVIEW_HEIGHT) {
                return option;
            }
        }

        return choices[0]; // Last resort
    }

    private final CameraDevice.StateCallback stateCallback = new CameraDevice.StateCallback() {
        @Override
        public void onOpened(@NonNull CameraDevice camera) {
            Log.d(TAG, "Camera opened successfully for Sinhala OCR");
            cameraDevice = camera;
            createCameraPreview();

            if (callback != null) {
                callback.onCameraReady();
            }
        }

        @Override
        public void onDisconnected(@NonNull CameraDevice camera) {
            Log.w(TAG, "Camera disconnected");
            cameraDevice.close();
            cameraDevice = null;

            if (callback != null) {
                callback.onCameraError("Camera disconnected");
            }
        }

        @Override
        public void onError(@NonNull CameraDevice camera, int error) {
            Log.e(TAG, "Camera error: " + error);
            cameraDevice.close();
            cameraDevice = null;

            String errorMessage = getErrorMessage(error);
            if (callback != null) {
                callback.onCameraError("Camera device error: " + errorMessage);
            }
        }

        private String getErrorMessage(int error) {
            switch (error) {
                case CameraDevice.StateCallback.ERROR_CAMERA_IN_USE:
                    return "Camera in use";
                case CameraDevice.StateCallback.ERROR_MAX_CAMERAS_IN_USE:
                    return "Max cameras in use";
                case CameraDevice.StateCallback.ERROR_CAMERA_DISABLED:
                    return "Camera disabled";
                case CameraDevice.StateCallback.ERROR_CAMERA_DEVICE:
                    return "Camera device error";
                case CameraDevice.StateCallback.ERROR_CAMERA_SERVICE:
                    return "Camera service error";
                default:
                    return "Unknown error (" + error + ")";
            }
        }
    };

    private void createCameraPreview() {
        try {
            textureView.getSurfaceTexture().setDefaultBufferSize(imageDimension.getWidth(), imageDimension.getHeight());
            Surface surface = new Surface(textureView.getSurfaceTexture());

            previewRequestBuilder = cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            previewRequestBuilder.addTarget(surface);

            // Optimize preview for document viewing
            setupPreviewRequestForSinhalaOCR(previewRequestBuilder);

            cameraDevice.createCaptureSession(Arrays.asList(surface, imageReader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                        @Override
                        public void onConfigured(@NonNull CameraCaptureSession session) {
                            if (cameraDevice == null) return;

                            captureSession = session;
                            try {
                                previewRequest = previewRequestBuilder.build();
                                captureSession.setRepeatingRequest(previewRequest, null, backgroundHandler);
                                Log.d(TAG, "Camera preview started successfully");
                            } catch (CameraAccessException e) {
                                Log.e(TAG, "Error starting camera preview", e);
                                if (callback != null) {
                                    callback.onCameraError("Preview start error");
                                }
                            }
                        }

                        @Override
                        public void onConfigureFailed(@NonNull CameraCaptureSession session) {
                            Log.e(TAG, "Camera preview configuration failed");
                            if (callback != null) {
                                callback.onCameraError("Preview configuration failed");
                            }
                        }
                    }, backgroundHandler);

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error creating camera preview", e);
            if (callback != null) {
                callback.onCameraError("Preview creation error: " + e.getMessage());
            }
        }
    }

    private void setupPreviewRequestForSinhalaOCR(CaptureRequest.Builder previewBuilder) {
        previewBuilder.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
        previewBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);
        previewBuilder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON);

        // Optimize for text visibility in preview
        previewBuilder.set(CaptureRequest.CONTROL_AWB_MODE, CaptureRequest.CONTROL_AWB_MODE_AUTO);
        previewBuilder.set(CaptureRequest.CONTROL_SCENE_MODE, CaptureRequest.CONTROL_SCENE_MODE_DISABLED);
    }

    private final ImageReader.OnImageAvailableListener onImageAvailableListener = new ImageReader.OnImageAvailableListener() {
        @Override
        public void onImageAvailable(ImageReader reader) {
            Log.d(TAG, "Image available for Sinhala OCR processing");

            Image image = reader.acquireLatestImage();
            if (image == null) {
                Log.w(TAG, "Acquired image is null");
                return;
            }

            try {
                // Convert Image to Bitmap optimized for Sinhala OCR
                Bitmap bitmap = imageToBitmap(image);
                if (bitmap != null) {
                    // Apply Sinhala OCR-specific image enhancements
                    Bitmap enhancedBitmap = enhanceImageForSinhalaOCR(bitmap);

                    if (callback != null) {
                        callback.onImageCaptured(enhancedBitmap);
                    }
                } else {
                    Log.e(TAG, "Failed to convert image to bitmap");
                    if (callback != null) {
                        callback.onCameraError("Image conversion failed");
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "Error processing captured image for Sinhala OCR", e);
                if (callback != null) {
                    callback.onCameraError("Image processing error: " + e.getMessage());
                }
            } finally {
                image.close();
            }
        }
    };

    private Bitmap imageToBitmap(Image image) {
        try {
            ByteBuffer buffer = image.getPlanes()[0].getBuffer();
            byte[] bytes = new byte[buffer.remaining()];
            buffer.get(bytes);
            return BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
        } catch (Exception e) {
            Log.e(TAG, "Error converting Image to Bitmap", e);
            return null;
        }
    }

    /**
     * Enhance image specifically for Sinhala OCR processing
     * Applies optimizations for Sinhala character recognition
     */
    private Bitmap enhanceImageForSinhalaOCR(Bitmap original) {
        try {
            Log.d(TAG, "Applying Sinhala OCR enhancements");

            // Create a mutable copy
            Bitmap enhanced = original.copy(Bitmap.Config.ARGB_8888, true);

            // Apply contrast enhancement for better Sinhala character visibility
            enhanced = adjustContrastForSinhala(enhanced, 1.3f);

            // Apply sharpening filter for Sinhala character clarity
            enhanced = sharpenImageForText(enhanced);

            // Ensure proper orientation for document reading
            enhanced = correctImageOrientation(enhanced);

            // Apply noise reduction while preserving text details
            enhanced = reduceNoisePreserveText(enhanced);

            Log.d(TAG, "Sinhala OCR enhancements applied successfully");
            return enhanced;

        } catch (Exception e) {
            Log.e(TAG, "Error enhancing image for Sinhala OCR", e);
            return original; // Return original if enhancement fails
        }
    }

    private Bitmap adjustContrastForSinhala(Bitmap bitmap, float contrast) {
        try {
            int width = bitmap.getWidth();
            int height = bitmap.getHeight();
            int[] pixels = new int[width * height];

            bitmap.getPixels(pixels, 0, width, 0, 0, width, height);

            for (int i = 0; i < pixels.length; i++) {
                int pixel = pixels[i];
                int alpha = (pixel >> 24) & 0xFF;
                int r = (int) Math.min(255, Math.max(0, ((((pixel >> 16) & 0xFF) - 128) * contrast) + 128));
                int g = (int) Math.min(255, Math.max(0, ((((pixel >> 8) & 0xFF) - 128) * contrast) + 128));
                int b = (int) Math.min(255, Math.max(0, (((pixel & 0xFF) - 128) * contrast) + 128));
                pixels[i] = (alpha << 24) | (r << 16) | (g << 8) | b;
            }

            Bitmap result = Bitmap.createBitmap(width, height, bitmap.getConfig());
            result.setPixels(pixels, 0, width, 0, 0, width, height);
            return result;

        } catch (Exception e) {
            Log.e(TAG, "Error adjusting contrast for Sinhala text", e);
            return bitmap;
        }
    }

    private Bitmap sharpenImageForText(Bitmap bitmap) {
        try {
            // Enhanced sharpening kernel for text clarity
            float[] sharpenKernel = {
                    -0.5f, -1.0f, -0.5f,
                    -1.0f,  6.0f, -1.0f,
                    -0.5f, -1.0f, -0.5f
            };

            return applyConvolutionFilter(bitmap, sharpenKernel);

        } catch (Exception e) {
            Log.e(TAG, "Error sharpening image for text", e);
            return bitmap;
        }
    }

    private Bitmap applyConvolutionFilter(Bitmap bitmap, float[] kernel) {
        try {
            int width = bitmap.getWidth();
            int height = bitmap.getHeight();
            Bitmap result = Bitmap.createBitmap(width, height, bitmap.getConfig());

            int[] pixels = new int[width * height];
            bitmap.getPixels(pixels, 0, width, 0, 0, width, height);

            int[] resultPixels = new int[width * height];

            int kernelSize = (int) Math.sqrt(kernel.length);
            int kernelRadius = kernelSize / 2;

            for (int y = kernelRadius; y < height - kernelRadius; y++) {
                for (int x = kernelRadius; x < width - kernelRadius; x++) {
                    float r = 0, g = 0, b = 0;
                    int a = (pixels[y * width + x] >> 24) & 0xFF;

                    for (int ky = -kernelRadius; ky <= kernelRadius; ky++) {
                        for (int kx = -kernelRadius; kx <= kernelRadius; kx++) {
                            int pixel = pixels[(y + ky) * width + (x + kx)];
                            float kernelVal = kernel[(ky + kernelRadius) * kernelSize + (kx + kernelRadius)];

                            r += ((pixel >> 16) & 0xFF) * kernelVal;
                            g += ((pixel >> 8) & 0xFF) * kernelVal;
                            b += (pixel & 0xFF) * kernelVal;
                        }
                    }

                    r = Math.min(255, Math.max(0, r));
                    g = Math.min(255, Math.max(0, g));
                    b = Math.min(255, Math.max(0, b));

                    resultPixels[y * width + x] = (a << 24) | ((int)r << 16) | ((int)g << 8) | (int)b;
                }
            }

            // Copy edge pixels
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    if (x < kernelRadius || x >= width - kernelRadius ||
                            y < kernelRadius || y >= height - kernelRadius) {
                        resultPixels[y * width + x] = pixels[y * width + x];
                    }
                }
            }

            result.setPixels(resultPixels, 0, width, 0, 0, width, height);
            return result;

        } catch (Exception e) {
            Log.e(TAG, "Error applying convolution filter", e);
            return bitmap;
        }
    }

    private Bitmap correctImageOrientation(Bitmap bitmap) {
        // For now, return as-is. Could be enhanced with automatic rotation detection
        // based on text orientation analysis
        return bitmap;
    }

    private Bitmap reduceNoisePreserveText(Bitmap bitmap) {
        try {
            // Light noise reduction that preserves text edges
            float[] noiseReductionKernel = {
                    0.0625f, 0.125f, 0.0625f,
                    0.125f,  0.25f,  0.125f,
                    0.0625f, 0.125f, 0.0625f
            };

            return applyConvolutionFilter(bitmap, noiseReductionKernel);

        } catch (Exception e) {
            Log.e(TAG, "Error reducing noise", e);
            return bitmap;
        }
    }

    private final TextureView.SurfaceTextureListener textureListener = new TextureView.SurfaceTextureListener() {
        @Override
        public void onSurfaceTextureAvailable(Surface surface, int width, int height) {
            Log.d(TAG, "SurfaceTexture available, opening camera for Sinhala OCR");
            openCamera();
        }

        @Override
        public void onSurfaceTextureSizeChanged(Surface surface, int width, int height) {
            Log.d(TAG, "SurfaceTexture size changed: " + width + "x" + height);
        }

        @Override
        public boolean onSurfaceTextureDestroyed(Surface surface) {
            Log.d(TAG, "SurfaceTexture destroyed");
            return false;
        }

        @Override
        public void onSurfaceTextureUpdated(Surface surface) {
            // Optionally provide preview frames for real-time document detection feedback
            if (callback != null && textureView.getBitmap() != null) {
                try {
                    Bitmap previewFrame = textureView.getBitmap();
                    if (previewFrame != null) {
                        callback.onPreviewFrame(previewFrame);
                    }
                } catch (Exception e) {
                    Log.w(TAG, "Error getting preview frame", e);
                }
            }
        }
    };

    private void closeCamera() {
        try {
            if (captureSession != null) {
                captureSession.close();
                captureSession = null;
            }

            if (cameraDevice != null) {
                cameraDevice.close();
                cameraDevice = null;
            }

            if (imageReader != null) {
                imageReader.close();
                imageReader = null;
            }

            Log.d(TAG, "Camera closed successfully");

        } catch (Exception e) {
            Log.e(TAG, "Error closing camera", e);
        }
    }

    private void startBackgroundThread() {
        backgroundThread = new HandlerThread("SinhalaOCRCamera");
        backgroundThread.start();
        backgroundHandler = new Handler(backgroundThread.getLooper());
        Log.d(TAG, "Background thread started for Sinhala OCR camera");
    }

    private void stopBackgroundThread() {
        try {
            if (backgroundThread != null) {
                backgroundThread.quitSafely();
                backgroundThread.join();
                backgroundThread = null;
                backgroundHandler = null;
                Log.d(TAG, "Background thread stopped");
            }
        } catch (InterruptedException e) {
            Log.e(TAG, "Error stopping background thread", e);
        }
    }

    /**
     * Focus the camera on a specific point for better document focus
     */
    public void focusOnDocument(float x, float y) {
        if (cameraDevice == null || captureSession == null || previewRequestBuilder == null) {
            Log.w(TAG, "Cannot focus - camera not ready");
            return;
        }

        try {
            // Create focus area for document
            int focusAreaSize = 150;
            Rect focusRect = new Rect(
                    Math.max(-1000, Math.min(1000, (int)(x * 2000 - focusAreaSize) - 1000)),
                    Math.max(-1000, Math.min(1000, (int)(y * 2000 - focusAreaSize) - 1000)),
                    Math.max(-1000, Math.min(1000, (int)(x * 2000 + focusAreaSize) - 1000)),
                    Math.max(-1000, Math.min(1000, (int)(y * 2000 + focusAreaSize) - 1000))
            );

            // Cancel any existing focus
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_CANCEL);
            captureSession.capture(previewRequestBuilder.build(), null, backgroundHandler);

            // Set new focus area optimized for document capture
            MeteringRectangle[] focusAreas = {new MeteringRectangle(focusRect, MeteringRectangle.METERING_WEIGHT_MAX)};
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_REGIONS, focusAreas);
            previewRequestBuilder.set(CaptureRequest.CONTROL_AE_REGIONS, focusAreas);
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_AUTO);
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_START);

            captureSession.capture(previewRequestBuilder.build(), null, backgroundHandler);

            // Reset to continuous focus
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_IDLE);
            previewRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);

            previewRequest = previewRequestBuilder.build();
            captureSession.setRepeatingRequest(previewRequest, null, backgroundHandler);

            Log.d(TAG, String.format("Focus set for document at: %.2f, %.2f", x, y));

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error setting document focus point", e);
        }
    }

    /**
     * Toggle flash for better document illumination
     */
    public void toggleFlash(boolean enabled) {
        if (!flashSupported) {
            Log.w(TAG, "Flash not supported on this device");
            return;
        }

        if (previewRequestBuilder == null || captureSession == null) {
            Log.w(TAG, "Cannot toggle flash - camera not ready");
            return;
        }

        try {
            if (enabled) {
                previewRequestBuilder.set(CaptureRequest.FLASH_MODE, CaptureRequest.FLASH_MODE_TORCH);
                Log.d(TAG, "Flash enabled for document illumination");
            } else {
                previewRequestBuilder.set(CaptureRequest.FLASH_MODE, CaptureRequest.FLASH_MODE_OFF);
                Log.d(TAG, "Flash disabled");
            }

            previewRequest = previewRequestBuilder.build();
            captureSession.setRepeatingRequest(previewRequest, null, backgroundHandler);

        } catch (CameraAccessException e) {
            Log.e(TAG, "Error toggling flash", e);
            if (callback != null) {
                callback.onCameraError("Flash control error");
            }
        }
    }

    /**
     * Get comprehensive camera information for debugging
     */
    public String getCameraInfo() {
        StringBuilder info = new StringBuilder();
        info.append(String.format("Camera ID: %s\n", cameraId != null ? cameraId : "Unknown"));
        info.append(String.format("Flash Support: %s\n", flashSupported ? "Yes" : "No"));
        info.append(String.format("AutoFocus Support: %s\n", autoFocusSupported ? "Yes" : "No"));
        info.append(String.format("Image Resolution: %dx%d\n",
                imageDimension != null ? imageDimension.getWidth() : 0,
                imageDimension != null ? imageDimension.getHeight() : 0));
        info.append(String.format("Currently Capturing: %s", isCapturing ? "Yes" : "No"));

        return info.toString();
    }

    /**
     * Check if camera is currently ready for capture
     */
    public boolean isCameraReady() {
        return cameraDevice != null && captureSession != null && !isCapturing;
    }

    /**
     * Check if flash is currently enabled
     */
    public boolean isFlashEnabled() {
        // This would need to track the current flash state
        // For now, return false as default
        return false;
    }

    /**
     * Get current image dimensions
     */
    public Size getImageDimensions() {
        return imageDimension;
    }
}