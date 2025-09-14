package com.research.blindassistant;

import android.graphics.Bitmap;

public interface SmartGlassesConnector {

    void setCallback(SmartGlassesCallback callback);
    void setFaceRecognitionService(FaceRecognitionService service);
    void connect();
    void startLiveFeed();
    void stopLiveFeed();
    void sendRecognitionData(String personName, String[] imagesBase64);
    void disconnect();
    void cleanup();
    boolean isConnected();
    boolean isReceivingFeed();

    interface SmartGlassesCallback {
        void onConnectionStatusChanged(boolean connected, String message);
        void onFrameReceived(Bitmap frame, long timestamp, double confidence);
        void onFeedStopped();
        void onPersonRegistered(String personName);
        void onError(String error);
    }
}