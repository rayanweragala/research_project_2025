package com.research.blindassistant;

import android.app.Activity;
import android.content.Context;
import android.util.Log;
import android.view.View;
import android.view.animation.*;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.core.content.ContextCompat;

public class StatusManager {

    public enum ConnectionStatus {
        DISCONNECTED,
        CONNECTING,
        CONNECTED,
        ERROR,
        IDLE,
        WAITING_INPUT,
        CHECKING_SERVER,
        READY_TO_CAPTURE,
        CAPTURING,
        PROCESSING,
        SUCCESS,
        ACTIVE
    }

    private ImageView statusIndicator;
    private View statusIndicatorBackground;
    private TextView statusText;
    private TextView statusSubtext;
    private View connectionPulse;

    private LinearLayout headerLayout;
    private Context context;

    public StatusManager(Activity activity) {
        this.context = activity;
        initializeViews(activity);
    }

    private void initializeViews(Activity activity) {
        statusIndicator = activity.findViewById(R.id.statusIndicator);
        statusIndicatorBackground = activity.findViewById(R.id.statusIndicatorBackground);
        statusText = activity.findViewById(R.id.statusText);
        statusSubtext = activity.findViewById(R.id.statusSubtext);
        connectionPulse = activity.findViewById(R.id.connectionPulse);
        headerLayout = activity.findViewById(R.id.headerLayout);
    }

    public void updateStatus(ConnectionStatus status) {
        updateStatus(status, null, null);
    }

    public void updateStatus(ConnectionStatus status, String customMessage, String customSubtext) {
        switch (status) {
            case DISCONNECTED:
                updateToDisconnectedState(customMessage, customSubtext);
                break;
            case CONNECTING:
                updateToConnectingState(customMessage, customSubtext);
                break;
            case CONNECTED:
                updateToConnectedState(customMessage, customSubtext);
                break;
            case ERROR:
                updateToErrorState(customMessage, customSubtext);
                break;
            case IDLE:
                updateToIdleState(customMessage, customSubtext);
                break;
            case WAITING_INPUT:
                updateToWaitingInputState(customMessage, customSubtext);
                break;
            case CHECKING_SERVER:
                updateToCheckingServerState(customMessage, customSubtext);
                break;
            case READY_TO_CAPTURE:
                updateToReadyToCaptureState(customMessage, customSubtext);
                break;
            case CAPTURING:
                updateToCapturingState(customMessage, customSubtext);
                break;
            case PROCESSING:
                updateToProcessingState(customMessage, customSubtext);
                break;
            case SUCCESS:
                updateToSuccessState(customMessage, customSubtext);
                break;
            case ACTIVE:
                updateToActiveState(customMessage, customSubtext);
                break;
        }
    }

    private void updateToDisconnectedState(String message , String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_visibility_off);
        statusIndicator.setColorFilter(ContextCompat.getColor(context,R.color.status_disconnected));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_disconnected);

        statusText.setText(message  != null ? message  : context.getString(R.string.smart_glasses_disconnected));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.tap_to_connect));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_disconnected_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_disconnected));

        connectionPulse.setVisibility(View.GONE);
        startPulseAnimation(connectionPulse);
    }

    private void updateToConnectingState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_sync);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_connecting));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_connecting);

        statusText.setText(message != null ? message : context.getString(R.string.connecting_smart_glasses));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.establishing_connection));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_connecting_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_connecting));

        connectionPulse.setVisibility(View.VISIBLE);
        startPulseAnimation(connectionPulse);

        startRotationAnimation(statusIndicator);
    }
    private void updateToConnectedState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_visibility_on);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_connected));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_connected);

        statusText.setText(message != null ? message : context.getString(R.string.smart_glasses_connected));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.ready_for_recognition));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_connected_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_connected));

        connectionPulse.setVisibility(View.GONE);

        statusIndicator.clearAnimation();
        startSuccessAnimation(statusIndicator);
    }

    private void updateToErrorState(String message, String subtext) {

        statusIndicator.setImageResource(R.drawable.ic_error);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_error));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_error);

        statusText.setText(message != null ? message : context.getString(R.string.connection_failed));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.check_connection_retry));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_error_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_error));

        connectionPulse.setVisibility(View.GONE);

        statusIndicator.clearAnimation();
        startShakeAnimation(statusIndicator);
    }

    private void updateToIdleState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_person);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_idle));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_idle);

        statusText.setText(message != null ? message : context.getString(R.string.status_idle));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.ready_to_start));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_idle_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_idle));

        connectionPulse.setVisibility(View.GONE);
        statusIndicator.clearAnimation();
    }

    private void updateToWaitingInputState(String message, String subtext) {
        if (statusIndicator == null) {
            Log.e("StatusManager", "statusIndicator is null in updateToWaitingInputState");
            return;
        }
        statusIndicator.setImageResource(R.drawable.ic_mic);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_waiting));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_waiting);

        statusText.setText(message != null ? message : context.getString(R.string.waiting_for_input));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.speak_to_continue));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_waiting_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_waiting));

        connectionPulse.setVisibility(View.VISIBLE);
        startPulseAnimation(connectionPulse);
        statusIndicator.clearAnimation();
    }

    private void updateToCheckingServerState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_cloud_sync);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_checking));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_checking);

        statusText.setText(message != null ? message : context.getString(R.string.checking_server));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.verifying_system));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_checking_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_checking));

        connectionPulse.setVisibility(View.VISIBLE);
        startPulseAnimation(connectionPulse);
        startRotationAnimation(statusIndicator);
    }

    private void updateToReadyToCaptureState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_camera_ready);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_ready));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_ready);

        statusText.setText(message != null ? message : context.getString(R.string.ready_to_capture));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.position_for_capture));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_ready_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_ready));

        connectionPulse.setVisibility(View.GONE);
        statusIndicator.clearAnimation();
        startReadyAnimation(statusIndicator);
    }

    private void updateToCapturingState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_camera_on);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_capturing));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_capturing);

        statusText.setText(message != null ? message : context.getString(R.string.capturing_face_data));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.taking_photos));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_capturing_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_capturing));

        connectionPulse.setVisibility(View.VISIBLE);
        startPulseAnimation(connectionPulse);
        startCaptureAnimation(statusIndicator);
    }

    private void updateToProcessingState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_processing);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_processing));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_processing);

        statusText.setText(message != null ? message : context.getString(R.string.processing_ai_model));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.saving_face_data));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_processing_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_processing));

        connectionPulse.setVisibility(View.VISIBLE);
        startPulseAnimation(connectionPulse);
        startRotationAnimation(statusIndicator);
    }

    private void updateToSuccessState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_check_circle);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_success));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_success);

        statusText.setText(message != null ? message : context.getString(R.string.registration_completed));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.person_registered_successfully));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_success_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_success));

        connectionPulse.setVisibility(View.GONE);
        statusIndicator.clearAnimation();
        startSuccessAnimation(statusIndicator);
    }

    private void updateToActiveState(String message, String subtext) {
        statusIndicator.setImageResource(R.drawable.ic_visibility_on);
        statusIndicator.setColorFilter(ContextCompat.getColor(context, R.color.status_active));
        statusIndicatorBackground.setBackgroundResource(R.drawable.status_indicator_background_active);

        statusText.setText(message != null ? message : context.getString(R.string.system_active));
        statusSubtext.setText(subtext != null ? subtext : context.getString(R.string.ready_for_operation));

        statusText.setTextColor(ContextCompat.getColor(context, R.color.status_active_text));
        headerLayout.setBackgroundColor(ContextCompat.getColor(context, R.color.header_background_active));

        connectionPulse.setVisibility(View.GONE);
        statusIndicator.clearAnimation();
    }
    private void startRotationAnimation(View view) {
        RotateAnimation rotate = new RotateAnimation(
                0f, 360f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f
        );
        rotate.setDuration(1000);
        rotate.setRepeatCount(Animation.INFINITE);
        rotate.setInterpolator(new LinearInterpolator());
        view.startAnimation(rotate);
    }

    private void startPulseAnimation(View view) {
        ScaleAnimation pulse = new ScaleAnimation(
                1.0f, 1.3f, 1.0f, 1.3f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f
        );
        pulse.setDuration(800);
        pulse.setRepeatCount(Animation.INFINITE);
        pulse.setRepeatMode(Animation.REVERSE);
        view.startAnimation(pulse);
    }

    private void startSuccessAnimation(View view) {
        ScaleAnimation success = new ScaleAnimation(
                1.0f, 1.2f, 1.0f, 1.2f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f
        );
        success.setDuration(300);
        success.setRepeatCount(1);
        success.setRepeatMode(Animation.REVERSE);
        view.startAnimation(success);
    }

    private void startShakeAnimation(View view) {
        TranslateAnimation shake = new TranslateAnimation(
                0, 10, 0, 0
        );
        shake.setDuration(100);
        shake.setRepeatCount(3);
        shake.setRepeatMode(Animation.REVERSE);
        view.startAnimation(shake);
    }

    private void startReadyAnimation(View view) {
        AlphaAnimation ready = new AlphaAnimation(1.0f, 0.7f);
        ready.setDuration(600);
        ready.setRepeatCount(Animation.INFINITE);
        ready.setRepeatMode(Animation.REVERSE);
        view.startAnimation(ready);
    }

    private void startCaptureAnimation(View view) {
        ScaleAnimation capture = new ScaleAnimation(
                1.0f, 1.1f, 1.0f, 1.1f,
                Animation.RELATIVE_TO_SELF, 0.5f,
                Animation.RELATIVE_TO_SELF, 0.5f
        );
        capture.setDuration(400);
        capture.setRepeatCount(Animation.INFINITE);
        capture.setRepeatMode(Animation.REVERSE);
        view.startAnimation(capture);
    }
}
