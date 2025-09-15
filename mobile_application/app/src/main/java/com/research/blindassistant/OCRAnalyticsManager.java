package com.research.blindassistant;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * Analytics manager for OCR operations
 * Tracks performance metrics, usage patterns, and error rates
 */
public class OCRAnalyticsManager {
    private static final String TAG = "OCRAnalytics";
    private static final String PREFS_NAME = "ocr_analytics";
    private static final String KEY_SESSION_DATA = "session_data";
    private static final String KEY_TOTAL_STATS = "total_stats";
    private static final String KEY_ERROR_LOG = "error_log";

    private Context context;
    private SharedPreferences preferences;
    private List<OCRSessionData> currentSessionData;
    private OCRStatistics totalStats;
    private long sessionStartTime;
    private int sessionId;

    public static class OCRSessionData {
        public long timestamp;
        public String documentType;
        public int textLength;
        public double confidence;
        public double processingTime;
        public boolean success;
        public String errorMessage;

        public OCRSessionData(String docType, int length, double conf, double procTime, boolean success) {
            this.timestamp = System.currentTimeMillis();
            this.documentType = docType;
            this.textLength = length;
            this.confidence = conf;
            this.processingTime = procTime;
            this.success = success;
        }

        public OCRSessionData(String errorMsg) {
            this.timestamp = System.currentTimeMillis();
            this.success = false;
            this.errorMessage = errorMsg;
        }
    }

    public static class OCRStatistics {
        public int totalSessions = 0;
        public int successfulOCRs = 0;
        public int failedOCRs = 0;
        public long totalProcessingTime = 0;
        public int totalCharactersExtracted = 0;
        public double averageConfidence = 0.0;
        public long totalUsageTime = 0;
        public String mostCommonDocumentType = "";
        public int documentTypeCounts = 0;

        public double getSuccessRate() {
            return totalSessions > 0 ? (double) successfulOCRs / totalSessions * 100 : 0.0;
        }

        public double getAverageProcessingTime() {
            return successfulOCRs > 0 ? (double) totalProcessingTime / successfulOCRs / 1000.0 : 0.0;
        }

        public double getCharactersPerDocument() {
            return successfulOCRs > 0 ? (double) totalCharactersExtracted / successfulOCRs : 0.0;
        }
    }

    public OCRAnalyticsManager(Context context) {
        this.context = context;
        this.preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        this.currentSessionData = new ArrayList<>();
        this.sessionStartTime = System.currentTimeMillis();
        this.sessionId = (int) (sessionStartTime / 1000);

        loadTotalStats();
        Log.d(TAG, "OCR Analytics Manager initialized for session " + sessionId);
    }

    private void loadTotalStats() {
        try {
            String statsJson = preferences.getString(KEY_TOTAL_STATS, "{}");
            JSONObject statsObj = new JSONObject(statsJson);

            totalStats = new OCRStatistics();
            totalStats.totalSessions = statsObj.optInt("totalSessions", 0);
            totalStats.successfulOCRs = statsObj.optInt("successfulOCRs", 0);
            totalStats.failedOCRs = statsObj.optInt("failedOCRs", 0);
            totalStats.totalProcessingTime = statsObj.optLong("totalProcessingTime", 0);
            totalStats.totalCharactersExtracted = statsObj.optInt("totalCharactersExtracted", 0);
            totalStats.averageConfidence = statsObj.optDouble("averageConfidence", 0.0);
            totalStats.totalUsageTime = statsObj.optLong("totalUsageTime", 0);
            totalStats.mostCommonDocumentType = statsObj.optString("mostCommonDocumentType", "Unknown");
            totalStats.documentTypeCounts = statsObj.optInt("documentTypeCounts", 0);

            Log.d(TAG, String.format("Loaded stats: %d total sessions, %.1f%% success rate",
                    totalStats.totalSessions, totalStats.getSuccessRate()));

        } catch (Exception e) {
            Log.w(TAG, "Error loading statistics, using defaults", e);
            totalStats = new OCRStatistics();
        }
    }

    private void saveTotalStats() {
        try {
            JSONObject statsObj = new JSONObject();
            statsObj.put("totalSessions", totalStats.totalSessions);
            statsObj.put("successfulOCRs", totalStats.successfulOCRs);
            statsObj.put("failedOCRs", totalStats.failedOCRs);
            statsObj.put("totalProcessingTime", totalStats.totalProcessingTime);
            statsObj.put("totalCharactersExtracted", totalStats.totalCharactersExtracted);
            statsObj.put("averageConfidence", totalStats.averageConfidence);
            statsObj.put("totalUsageTime", totalStats.totalUsageTime);
            statsObj.put("mostCommonDocumentType", totalStats.mostCommonDocumentType);
            statsObj.put("documentTypeCounts", totalStats.documentTypeCounts);

            preferences.edit()
                    .putString(KEY_TOTAL_STATS, statsObj.toString())
                    .apply();

            Log.d(TAG, "Statistics saved successfully");

        } catch (JSONException e) {
            Log.e(TAG, "Error saving statistics", e);
        }
    }

    public void logOCRSuccess(String documentType, int textLength, double confidence, double processingTime) {
        OCRSessionData data = new OCRSessionData(documentType, textLength, confidence, processingTime, true);
        currentSessionData.add(data);

        // Update total statistics
        totalStats.successfulOCRs++;
        totalStats.totalCharactersExtracted += textLength;
        totalStats.totalProcessingTime += (long)(processingTime * 1000);

        // Update average confidence (running average)
        totalStats.averageConfidence = ((totalStats.averageConfidence * (totalStats.successfulOCRs - 1)) + confidence) / totalStats.successfulOCRs;

        Log.d(TAG, String.format("OCR Success logged: %s, %d chars, %.1f%% confidence, %.2fs",
                documentType, textLength, confidence * 100, processingTime));

        saveTotalStats();
    }

    public void logOCRError(String errorMessage) {
        OCRSessionData data = new OCRSessionData(errorMessage);
        currentSessionData.add(data);

        totalStats.failedOCRs++;

        Log.w(TAG, "OCR Error logged: " + errorMessage);

        // Also log to error log
        logError(errorMessage);
        saveTotalStats();
    }

    private void logError(String errorMessage) {
        try {
            String timestamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date());
            String errorEntry = timestamp + ": " + errorMessage;

            String existingErrors = preferences.getString(KEY_ERROR_LOG, "");
            String updatedErrors = existingErrors + "\n" + errorEntry;

            // Keep only last 100 error entries to prevent excessive storage
            String[] lines = updatedErrors.split("\n");
            if (lines.length > 100) {
                StringBuilder trimmed = new StringBuilder();
                for (int i = lines.length - 100; i < lines.length; i++) {
                    trimmed.append(lines[i]).append("\n");
                }
                updatedErrors = trimmed.toString();
            }

            preferences.edit()
                    .putString(KEY_ERROR_LOG, updatedErrors)
                    .apply();

        } catch (Exception e) {
            Log.e(TAG, "Error logging error message", e);
        }
    }

    public void logTextSaved(String filename, int textLength) {
        Log.d(TAG, String.format("Text saved: %s (%d characters)", filename, textLength));

        // Could extend to track save statistics if needed
    }

    public void logVoiceCommand(String command, boolean recognized) {
        Log.d(TAG, String.format("Voice command: '%s' - %s", command, recognized ? "recognized" : "not recognized"));

        // Could extend to track voice interaction statistics
    }

    public void saveSession() {
        if (currentSessionData.isEmpty()) {
            Log.d(TAG, "No session data to save");
            return;
        }

        try {
            // Calculate session duration
            long sessionDuration = System.currentTimeMillis() - sessionStartTime;
            totalStats.totalUsageTime += sessionDuration;
            totalStats.totalSessions++;

            // Save session data
            JSONArray sessionArray = new JSONArray();
            for (OCRSessionData data : currentSessionData) {
                JSONObject dataObj = new JSONObject();
                dataObj.put("timestamp", data.timestamp);
                dataObj.put("documentType", data.documentType != null ? data.documentType : "");
                dataObj.put("textLength", data.textLength);
                dataObj.put("confidence", data.confidence);
                dataObj.put("processingTime", data.processingTime);
                dataObj.put("success", data.success);
                dataObj.put("errorMessage", data.errorMessage != null ? data.errorMessage : "");
                sessionArray.put(dataObj);
            }

            // Store session with timestamp key
            String sessionKey = KEY_SESSION_DATA + "_" + sessionId;
            preferences.edit()
                    .putString(sessionKey, sessionArray.toString())
                    .apply();

            saveTotalStats();

            Log.d(TAG, String.format("Session saved: %d operations in %.1f minutes",
                    currentSessionData.size(), sessionDuration / 60000.0));

        } catch (JSONException e) {
            Log.e(TAG, "Error saving session data", e);
        }
    }

    public OCRStatistics getTotalStatistics() {
        return totalStats;
    }

    public List<OCRSessionData> getCurrentSessionData() {
        return new ArrayList<>(currentSessionData);
    }

    public String getSessionSummary() {
        int successCount = 0;
        int errorCount = 0;
        int totalChars = 0;
        double totalTime = 0;

        for (OCRSessionData data : currentSessionData) {
            if (data.success) {
                successCount++;
                totalChars += data.textLength;
                totalTime += data.processingTime;
            } else {
                errorCount++;
            }
        }

        long sessionDuration = (System.currentTimeMillis() - sessionStartTime) / 1000;

        return String.format(Locale.getDefault(),
                "Session Summary:\n" +
                        "Duration: %d seconds\n" +
                        "Successful OCRs: %d\n" +
                        "Failed OCRs: %d\n" +
                        "Characters extracted: %d\n" +
                        "Average processing time: %.2f seconds\n" +
                        "Success rate: %.1f%%",
                sessionDuration, successCount, errorCount, totalChars,
                successCount > 0 ? totalTime / successCount : 0,
                currentSessionData.size() > 0 ? (double) successCount / currentSessionData.size() * 100 : 0);
    }

    public String getOverallSummary() {
        return String.format(Locale.getDefault(),
                "Overall Statistics:\n" +
                        "Total sessions: %d\n" +
                        "Total successful OCRs: %d\n" +
                        "Total failed OCRs: %d\n" +
                        "Success rate: %.1f%%\n" +
                        "Characters extracted: %d\n" +
                        "Average confidence: %.1f%%\n" +
                        "Average processing time: %.2f seconds\n" +
                        "Average characters per document: %.0f\n" +
                        "Total usage time: %.1f hours",
                totalStats.totalSessions,
                totalStats.successfulOCRs,
                totalStats.failedOCRs,
                totalStats.getSuccessRate(),
                totalStats.totalCharactersExtracted,
                totalStats.averageConfidence * 100,
                totalStats.getAverageProcessingTime(),
                totalStats.getCharactersPerDocument(),
                totalStats.totalUsageTime / 3600000.0);
    }

    public String getRecentErrors() {
        return preferences.getString(KEY_ERROR_LOG, "No recent errors");
    }

    public void clearAllData() {
        preferences.edit()
                .remove(KEY_SESSION_DATA)
                .remove(KEY_TOTAL_STATS)
                .remove(KEY_ERROR_LOG)
                .apply();

        currentSessionData.clear();
        totalStats = new OCRStatistics();

        Log.d(TAG, "All analytics data cleared");
    }

    public boolean hasSignificantUsage() {
        return totalStats.totalSessions >= 5;
    }

    public double getRecentSuccessRate() {
        if (currentSessionData.isEmpty()) {
            return 0.0;
        }

        int successCount = 0;
        for (OCRSessionData data : currentSessionData) {
            if (data.success) {
                successCount++;
            }
        }

        return (double) successCount / currentSessionData.size() * 100;
    }

    public void logPerformanceMetric(String metricName, double value) {
        Log.d(TAG, String.format("Performance metric - %s: %.3f", metricName, value));

        // Could be extended to track custom performance metrics
    }
}