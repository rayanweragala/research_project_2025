package com.research.blindassistant;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.util.Log;

public class BootReceiver extends BroadcastReceiver {
    private static final String TAG = "BootReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
                SharedPreferences prefs = context.getSharedPreferences("blind_assistant_prefs", Context.MODE_PRIVATE);
                boolean autoStart = prefs.getBoolean("monitoring_enabled", true);
                if (autoStart) {
                    Intent svc = new Intent(context, SmartGlassesForegroundService.class);
                    svc.setAction(SmartGlassesForegroundService.ACTION_START);
                    context.startForegroundService(svc);
                    Log.d(TAG, "Monitoring service auto-started after boot");
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to handle boot event", e);
        }
    }
}



