package com.research.blindassistant;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public class StringResources {

    private static Locale currentLocale = Locale.US;

    public static final Locale LOCALE_ENGLISH = Locale.US;
    public static final Locale LOCALE_SINHALA = new Locale("si", "LK");

    public static void setLocale(Locale locale) {
        currentLocale = locale;
    }

    public static Locale getCurrentLocale() {
        return currentLocale;
    }

    public static String getString(String stringId) {
        return getLocalizedString(stringId, currentLocale);
    }

    public static String getLocalizedString(String stringId, Locale locale) {
        Map<Locale, String> localizations = STRING_RESOURCES.get(stringId);
        if (localizations != null) {
            String localizedString = localizations.get(locale);
            if (localizedString != null) {
                return localizedString;
            }
            return localizations.get(LOCALE_ENGLISH);
        }
        return stringId;
    }

    public static final class Main {
        public static final String ASSISTANT_READY = "main_assistant_ready";
        public static final String FACE_RECOGNITION_STARTING = "main_face_recognition_starting";
        public static final String NAVIGATION_STARTING = "main_navigation_starting";
        public static final String SETTINGS_OPENING = "main_settings_opening";
        public static final String BUTTON_TAP_ACTIVATE = "main_button_tap_activate";
        public static final String VOICE_COMMAND_ACTIVATED = "main_voice_command_activated";
        public static final String OPENING_FACE_RECOGNITION = "main_opening_face_recognition";
        public static final String OPENING_NAVIGATION = "main_opening_navigation";
        public static final String STOPPING_VOICE_COMMANDS = "main_stopping_voice_commands";
        public static final String COMMAND_NOT_RECOGNIZED = "main_command_not_recognized";
        public static final String MIC_PERMISSION_REQUIRED = "main_mic_permission_required";

        public static final String ERROR_AUDIO = "main_error_audio";
        public static final String ERROR_CLIENT = "main_error_client";
        public static final String ERROR_INSUFFICIENT_PERMISSIONS = "main_error_insufficient_permissions";
        public static final String ERROR_NETWORK = "main_error_network";
        public static final String ERROR_NETWORK_TIMEOUT = "main_error_network_timeout";
        public static final String ERROR_NO_MATCH = "main_error_no_match";
        public static final String ERROR_RECOGNIZER_BUSY = "main_error_recognizer_busy";
        public static final String ERROR_SERVER = "main_error_server";
        public static final String ERROR_SPEECH_TIMEOUT = "main_error_speech_timeout";

        public static final String STOP_OBSTACLES_NEAR = "main_stop_obstacles_near";

    }

    public static final class FaceRecognition {
        public static final String SMART_GLASSES_READY = "face_smart_glasses_ready";
        public static final String BACK_TO_MAIN = "face_back_to_main";
        public static final String OPENING_REGISTRATION = "face_opening_registration";
        public static final String BUTTON_PREFIX = "face_button_prefix";
        public static final String SMART_GLASSES_CONNECTED = "face_smart_glasses_connected";
        public static final String SERVER_CONNECTED = "face_server_connected";
        public static final String CAMERA_ACTIVATED = "face_camera_activated";
        public static final String SERVER_NOT_CONNECTED = "face_server_not_connected";
        public static final String STARTING_CAMERA = "face_starting_camera";
        public static final String CAMERA_NOT_ACTIVE = "face_camera_not_active";
        public static final String RECOGNITION_STARTED = "face_recognition_started";
        public static final String RECOGNITION_STOPPED = "face_recognition_stopped";
        public static final String PERSON_IDENTIFIED = "face_person_identified";
        public static final String COMMANDS_AVAILABLE_ACTIVE = "face_commands_available_active";
        public static final String COMMANDS_AVAILABLE_INACTIVE = "face_commands_available_inactive";
        public static final String AUDIO_PERMISSION_GRANTED = "face_audio_permission_granted";
        public static final String MIC_PERMISSION_REQUIRED = "face_mic_permission_required";
    }

    public static final class AddFriend {
        public static final String SPEECH_RECOGNITION_UNAVAILABLE = "add_speech_recognition_unavailable";
        public static final String CANCELING_REGISTRATION = "add_canceling_registration";
        public static final String STARTING_OVER = "add_starting_over";
        public static final String BUTTON_PREFIX = "add_button_prefix";
        public static final String FACE_REGISTRATION_READY = "add_face_registration_ready";
        public static final String NAME_CONFIRMATION = "add_name_confirmation";
        public static final String STOPPING_CAPTURE = "add_stopping_capture";
        public static final String NAME_NOT_CAUGHT = "add_name_not_caught";
        public static final String HEARING_TROUBLE = "add_hearing_trouble";
        public static final String FACE_SMART_GLASSES = "add_face_smart_glasses";
        public static final String CAPTURE_COMPLETE = "add_capture_complete";
        public static final String CAPTURE_STOPPED = "add_capture_stopped";
        public static final String ERROR_PREFIX = "add_error_prefix";
        public static final String SMART_GLASSES_CONNECTED = "add_smart_glasses_connected";
        public static final String CONNECTION_FAILED = "add_connection_failed";
        public static final String REGISTRATION_SUCCESSFUL = "add_registration_successful";
        public static final String FACE_REGISTRATION_SUCCESSFUL = "add_face_registration_successful";
        public static final String REGISTRATION_FAILED = "add_registration_failed";
        public static final String SERVER_ERROR = "add_server_error";
        public static final String SERVER_READY = "add_server_ready";
        public static final String SERVER_NOT_RESPONDING = "add_server_not_responding";
        public static final String SPEECH_UNAVAILABLE = "add_speech_unavailable";
        public static final String NETWORK_ERROR = "add_network_error";
    }

    public static final class Settings {
        public static final String BACK_TO_MAIN = "settings_back_to_main";
        public static final String SCREEN_OPEN = "settings_screen_open";
        public static final String BACK_BUTTON_DESC = "back_button_desc";
    }


    private static final Map<String, Map<Locale, String>> STRING_RESOURCES = new HashMap<>();
    
    static {
        addString(Main.ASSISTANT_READY, LOCALE_ENGLISH, 
                "Assistant ready. Say commands like face, voice, navigation, or settings. Or tap any button.");
        addString(Main.FACE_RECOGNITION_STARTING, LOCALE_ENGLISH, 
                "Starting face recognition");
        addString(Main.NAVIGATION_STARTING, LOCALE_ENGLISH, 
                "Navigation assistance starting");
        addString(Main.SETTINGS_OPENING, LOCALE_ENGLISH, 
                "Opening settings");
        addString(Main.BUTTON_TAP_ACTIVATE, LOCALE_ENGLISH, 
                "Button: %s. Tap to activate");
        addString(Main.VOICE_COMMAND_ACTIVATED, LOCALE_ENGLISH, 
                "Voice command activated. I'm listening....");
        addString(Main.OPENING_FACE_RECOGNITION, LOCALE_ENGLISH, 
                "Opening face recognition");
        addString(Main.OPENING_NAVIGATION, LOCALE_ENGLISH, 
                "Opening navigation assistance");
        addString(Main.STOPPING_VOICE_COMMANDS, LOCALE_ENGLISH, 
                "Stopping voice commands");
        addString(Main.COMMAND_NOT_RECOGNIZED, LOCALE_ENGLISH, 
                "Command not recognized, try saying face, navigation, settings or stop");
        addString(Main.MIC_PERMISSION_REQUIRED, LOCALE_ENGLISH, 
                "Microphone permission required for voice commands");
        addString(Main.STOP_OBSTACLES_NEAR, LOCALE_ENGLISH,
                "Stop obstacles near");


        addString(Main.ERROR_AUDIO, LOCALE_ENGLISH, "Audio recording error");
        addString(Main.ERROR_CLIENT, LOCALE_ENGLISH, "Client side error");
        addString(Main.ERROR_INSUFFICIENT_PERMISSIONS, LOCALE_ENGLISH, "Insufficient permissions");
        addString(Main.ERROR_NETWORK, LOCALE_ENGLISH, "Network error");
        addString(Main.ERROR_NETWORK_TIMEOUT, LOCALE_ENGLISH, "Network timeout");
        addString(Main.ERROR_NO_MATCH, LOCALE_ENGLISH, "No speech match found. Try again.");
        addString(Main.ERROR_RECOGNIZER_BUSY, LOCALE_ENGLISH, "Speech recognizer busy");
        addString(Main.ERROR_SERVER, LOCALE_ENGLISH, "Server error");
        addString(Main.ERROR_SPEECH_TIMEOUT, LOCALE_ENGLISH, "Speech timeout");

        addString(FaceRecognition.SMART_GLASSES_READY, LOCALE_ENGLISH, 
                "Smart glasses interface ready. Connecting to camera server.");
        addString(FaceRecognition.BACK_TO_MAIN, LOCALE_ENGLISH, 
                "Going back to main menu");
        addString(FaceRecognition.OPENING_REGISTRATION, LOCALE_ENGLISH, 
                "Opening face registration");
        addString(FaceRecognition.BUTTON_PREFIX, LOCALE_ENGLISH, 
                "Button: %s");
        addString(FaceRecognition.SMART_GLASSES_CONNECTED, LOCALE_ENGLISH, 
                "Smart glasses connected. Camera active. %d people registered.");
        addString(FaceRecognition.SERVER_CONNECTED, LOCALE_ENGLISH, 
                "Server connected with %d people registered. Starting camera...");
        addString(FaceRecognition.CAMERA_ACTIVATED, LOCALE_ENGLISH, 
                "Smart glasses camera activated");
        addString(FaceRecognition.SERVER_NOT_CONNECTED, LOCALE_ENGLISH, 
                "Smart glasses server not connected. Please check connection.");
        addString(FaceRecognition.STARTING_CAMERA, LOCALE_ENGLISH, 
                "Starting smart glass camera....");
        addString(FaceRecognition.CAMERA_NOT_ACTIVE, LOCALE_ENGLISH, 
                "Smart glasses camera not active. Please check connection.");
        addString(FaceRecognition.RECOGNITION_STARTED, LOCALE_ENGLISH, 
                "Face recognition started. Processing smart glasses camera feed.");
        addString(FaceRecognition.RECOGNITION_STOPPED, LOCALE_ENGLISH, 
                "Face recognition stopped");
        addString(FaceRecognition.PERSON_IDENTIFIED, LOCALE_ENGLISH, 
                "%s identified");
        addString(FaceRecognition.COMMANDS_AVAILABLE_ACTIVE, LOCALE_ENGLISH, 
                "Commands available: stop, add friend, stats, or back");
        addString(FaceRecognition.COMMANDS_AVAILABLE_INACTIVE, LOCALE_ENGLISH, 
                "Commands available: start, add friend, or back");
        addString(FaceRecognition.AUDIO_PERMISSION_GRANTED, LOCALE_ENGLISH, 
                "Audio permission granted. Smart glasses interface ready.");
        addString(FaceRecognition.MIC_PERMISSION_REQUIRED, LOCALE_ENGLISH, 
                "Microphone permission is required for voice commands.");

        addString(AddFriend.SPEECH_RECOGNITION_UNAVAILABLE, LOCALE_ENGLISH, 
                "Speech recognition is not available on this device");
        addString(AddFriend.CANCELING_REGISTRATION, LOCALE_ENGLISH, 
                "Canceling face registration");
        addString(AddFriend.STARTING_OVER, LOCALE_ENGLISH, 
                "Starting over");
        addString(AddFriend.BUTTON_PREFIX, LOCALE_ENGLISH, 
                "Button: %s");
        addString(AddFriend.FACE_REGISTRATION_READY, LOCALE_ENGLISH, 
                "Face registration ready. First, tell me the person's name.");
        addString(AddFriend.NAME_CONFIRMATION, LOCALE_ENGLISH, 
                "Got it! Name is %s. Now checking face recognition server.");
        addString(AddFriend.STOPPING_CAPTURE, LOCALE_ENGLISH, 
                "Stopping capture");
        addString(AddFriend.NAME_NOT_CAUGHT, LOCALE_ENGLISH, 
                "I didn't catch that. Please say the person's name again.");
        addString(AddFriend.HEARING_TROUBLE, LOCALE_ENGLISH, 
                "I'm having trouble hearing you. Please use the start over button to try again.");
        addString(AddFriend.FACE_SMART_GLASSES, LOCALE_ENGLISH, 
                "Ask %s to face the smart glasses. I'll automatically take the best photos.");
        addString(AddFriend.CAPTURE_COMPLETE, LOCALE_ENGLISH, 
                "Perfect! I've captured %d excellent photos of %s. Now registering with the system.");
        addString(AddFriend.CAPTURE_STOPPED, LOCALE_ENGLISH, 
                "Capture stopped: %s");
        addString(AddFriend.ERROR_PREFIX, LOCALE_ENGLISH, 
                "Error: %s");
        addString(AddFriend.SMART_GLASSES_CONNECTED, LOCALE_ENGLISH, 
                "Smart glasses connected successfully!");
        addString(AddFriend.CONNECTION_FAILED, LOCALE_ENGLISH, 
                "Connection failed: %s");
        addString(AddFriend.REGISTRATION_SUCCESSFUL, LOCALE_ENGLISH, 
                "Excellent! %s has been successfully registered in the smart glasses system. They will now be recognized automatically.");
        addString(AddFriend.FACE_REGISTRATION_SUCCESSFUL, LOCALE_ENGLISH, 
                "Face registration successful! %s");
        addString(AddFriend.REGISTRATION_FAILED, LOCALE_ENGLISH, 
                "Registration failed: %s");
        addString(AddFriend.SERVER_ERROR, LOCALE_ENGLISH, 
                "Face recognition server error: %s");
        addString(AddFriend.SERVER_READY, LOCALE_ENGLISH, 
                "Face recognition server is ready. %d people currently registered. Now connecting to smart glasses.");
        addString(AddFriend.SERVER_NOT_RESPONDING, LOCALE_ENGLISH, 
                "Face recognition server is not responding");
        addString(AddFriend.SPEECH_UNAVAILABLE, LOCALE_ENGLISH, 
                "Speech recognition unavailable. Please use the buttons to navigate.");
        addString(AddFriend.NETWORK_ERROR, LOCALE_ENGLISH, 
                "Network error. Please check your connection and try again.");
        addString(Settings.BACK_TO_MAIN, LOCALE_ENGLISH, "Going back to main menu");
        addString(Settings.SCREEN_OPEN, LOCALE_ENGLISH, "Settings screen opened. Select language preference.");
        addString(Settings.BACK_BUTTON_DESC, LOCALE_ENGLISH, "Back button. Tap to return to main menu.");

        addString(Main.ASSISTANT_READY, LOCALE_SINHALA,
                "සහායක සූදානම්. මුහුණ, හඬ, සංචාලනය, හෝ සැකසුම් වැනි විධාන කියන්න. නැතහොත් ඕනෑම බොත්තමක් තට්ටු කරන්න.");
        addString(Main.FACE_RECOGNITION_STARTING, LOCALE_SINHALA,
                "මුහුණු හඳුනාගැනීම ආරම්භ කරමින්");
        addString(Main.NAVIGATION_STARTING, LOCALE_SINHALA, 
                "සංචාලන සහාය ආරම්භ වෙමින්");
        addString(Main.SETTINGS_OPENING, LOCALE_SINHALA, 
                "සැකසුම් විවෘත කරමින්");
        addString(Main.BUTTON_TAP_ACTIVATE, LOCALE_SINHALA,
                "බොත්තම: %s. සක්‍රිය කිරීමට තට්ටු කරන්න");
        addString(Main.VOICE_COMMAND_ACTIVATED, LOCALE_SINHALA, 
                "හඬ විධානය සක්‍රිය කර ඇත. මම සවන් දෙමින් සිටිමි....");
        addString(Main.OPENING_FACE_RECOGNITION, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීම විවෘත කරමින්");
        addString(Main.OPENING_NAVIGATION, LOCALE_SINHALA, 
                "සංචාලන සහාය විවෘත කරමින්");
        addString(Main.STOPPING_VOICE_COMMANDS, LOCALE_SINHALA, 
                "හඬ විධාන නවත්වමින්");
        addString(Main.COMMAND_NOT_RECOGNIZED, LOCALE_SINHALA, 
                "විධානය හඳුනාගත නොහැක, මුහුණ, සංචාලනය, සැකසුම් හෝ නවත්වන්න යැයි කීමට උත්සාහ කරන්න");
        addString(Main.MIC_PERMISSION_REQUIRED, LOCALE_SINHALA, 
                "හඬ විධාන සඳහා මයික්‍රෆෝන් අවසරය අවශ්‍ය වේ");

        addString(Main.ERROR_AUDIO, LOCALE_SINHALA, "ශ්‍රව්‍ය පටිගත කිරීමේ දෝෂයකි");
        addString(Main.ERROR_CLIENT, LOCALE_SINHALA, "සේවාදායක දෝෂයකි");
        addString(Main.ERROR_INSUFFICIENT_PERMISSIONS, LOCALE_SINHALA, "ප්‍රමාණවත් නොවන අවසර");
        addString(Main.ERROR_NETWORK, LOCALE_SINHALA, "ජාල දෝෂයකි");
        addString(Main.ERROR_NETWORK_TIMEOUT, LOCALE_SINHALA, "ජාල කාල නිමාව");
        addString(Main.ERROR_NO_MATCH, LOCALE_SINHALA, "කථන ගැලපීමක් හමු නොවීය. නැවත උත්සාහ කරන්න.");
        addString(Main.ERROR_RECOGNIZER_BUSY, LOCALE_SINHALA, "කථන හඳුනාගැනීම කාර්යබහුලයි");
        addString(Main.ERROR_SERVER, LOCALE_SINHALA, "සේවාදායක දෝෂයකි");
        addString(Main.ERROR_SPEECH_TIMEOUT, LOCALE_SINHALA, "කථන කාල නිමාව");

        addString(FaceRecognition.SMART_GLASSES_READY, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි අතුරුමුහුණත සූදානම්. කැමරා සේවාදායකයට සම්බන්ධ වෙමින්.");
        addString(FaceRecognition.BACK_TO_MAIN, LOCALE_SINHALA, 
                "ප්‍රධාන මෙනුවට ආපසු යමින්");
        addString(FaceRecognition.OPENING_REGISTRATION, LOCALE_SINHALA, 
                "මුහුණු ලියාපදිංචිය විවෘත කරමින්");
        addString(FaceRecognition.BUTTON_PREFIX, LOCALE_SINHALA, 
                "බොත්තම: %s");
        addString(FaceRecognition.SMART_GLASSES_CONNECTED, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි සම්බන්ධ කර ඇත. කැමරාව සක්‍රියයි. %d දෙනෙකු ලියාපදිංචි කර ඇත.");
        addString(FaceRecognition.SERVER_CONNECTED, LOCALE_SINHALA, 
                "සේවාදායකය %d දෙනෙකු ලියාපදිංචි කර ඇති අතර සම්බන්ධ වී ඇත. කැමරාව ආරම්භ කරමින්...");
        addString(FaceRecognition.CAMERA_ACTIVATED, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි කැමරාව සක්‍රිය කර ඇත");
        addString(FaceRecognition.SERVER_NOT_CONNECTED, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි සේවාදායකය සම්බන්ධ කර නැත. කරුණාකර සම්බන්ධතාවය පරීක්ෂා කරන්න.");
        addString(FaceRecognition.STARTING_CAMERA, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි කැමරාව ආරම්භ කරමින්....");
        addString(FaceRecognition.CAMERA_NOT_ACTIVE, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි කැමරාව සක්‍රිය නොවේ. කරුණාකර සම්බන්ධතාවය පරීක්ෂා කරන්න.");
        addString(FaceRecognition.RECOGNITION_STARTED, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීම ආරම්භ විය. ස්මාර්ට් කණ්ණාඩි කැමරා ප්‍රවාහය සැකසීම.");
        addString(FaceRecognition.RECOGNITION_STOPPED, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීම නතර විය");
        addString(FaceRecognition.PERSON_IDENTIFIED, LOCALE_SINHALA, 
                "%s හඳුනාගෙන ඇත");
        addString(FaceRecognition.COMMANDS_AVAILABLE_ACTIVE, LOCALE_SINHALA, 
                "ලබා ගත හැකි විධාන: නවත්වන්න, මිතුරෙකු එකතු කරන්න, සංඛ්‍යාලේඛන, හෝ ආපසු");
        addString(FaceRecognition.COMMANDS_AVAILABLE_INACTIVE, LOCALE_SINHALA, 
                "ලබා ගත හැකි විධාන: ආරම්භ කරන්න, මිතුරෙකු එකතු කරන්න, හෝ ආපසු");
        addString(FaceRecognition.AUDIO_PERMISSION_GRANTED, LOCALE_SINHALA, 
                "ශ්‍රව්‍ය අවසරය ලබා දී ඇත. ස්මාර්ට් කණ්ණාඩි අතුරුමුහුණත සූදානම්.");
        addString(FaceRecognition.MIC_PERMISSION_REQUIRED, LOCALE_SINHALA, 
                "හඬ විධාන සඳහා මයික්‍රෆෝන් අවසරය අවශ්‍ය වේ.");

        addString(AddFriend.SPEECH_RECOGNITION_UNAVAILABLE, LOCALE_SINHALA, 
                "මෙම උපකරණයේ කථන හඳුනාගැනීම නොමැත");
        addString(AddFriend.CANCELING_REGISTRATION, LOCALE_SINHALA, 
                "මුහුණු ලියාපදිංචිය අවලංගු කරමින්");
        addString(AddFriend.STARTING_OVER, LOCALE_SINHALA, 
                "නැවත ආරම්භ කරමින්");
        addString(AddFriend.BUTTON_PREFIX, LOCALE_SINHALA, 
                "බොත්තම: %s");
        addString(AddFriend.FACE_REGISTRATION_READY, LOCALE_SINHALA, 
                "මුහුණු ලියාපදිංචිය සූදානම්. පළමුව, පුද්ගලයාගේ නම මට කියන්න.");
        addString(AddFriend.NAME_CONFIRMATION, LOCALE_SINHALA, 
                "තේරුණා! නම %s. දැන් මුහුණු හඳුනාගැනීමේ සේවාදායකය පරීක්ෂා කරමින්.");
        addString(AddFriend.STOPPING_CAPTURE, LOCALE_SINHALA, 
                "ග්‍රහණය නවත්වමින්");
        addString(AddFriend.NAME_NOT_CAUGHT, LOCALE_SINHALA, 
                "මට ඒක තේරුණේ නැහැ. කරුණාකර පුද්ගලයාගේ නම නැවත කියන්න.");
        addString(AddFriend.HEARING_TROUBLE, LOCALE_SINHALA, 
                "ඔබ කියන දේ ඇසීමට මට අපහසුයි. කරුණාකර නැවත උත්සාහ කිරීමට නැවත ආරම්භ බොත්තම භාවිතා කරන්න.");
        addString(AddFriend.FACE_SMART_GLASSES, LOCALE_SINHALA, 
                "%s ට ස්මාර්ට් කණ්ණාඩි දෙසට මුහුණ දෙන ලෙස ඉල්ලන්න. මම ස්වයංක්‍රීයව හොඳම ඡායාරූප ගන්නෙමි.");
        addString(AddFriend.CAPTURE_COMPLETE, LOCALE_SINHALA, 
                "නියමයි! මම %s ගේ විශිෂ්ට ඡායාරූප %d ක් ග්‍රහණය කර ඇත. දැන් පද්ධතිය සමඟ ලියාපදිංචි වෙමින්.");
        addString(AddFriend.CAPTURE_STOPPED, LOCALE_SINHALA, 
                "ග්‍රහණය නතර විය: %s");
        addString(AddFriend.ERROR_PREFIX, LOCALE_SINHALA, 
                "දෝෂය: %s");
        addString(AddFriend.SMART_GLASSES_CONNECTED, LOCALE_SINHALA, 
                "ස්මාර්ට් කණ්ණාඩි සාර්ථකව සම්බන්ධ විය!");
        addString(AddFriend.CONNECTION_FAILED, LOCALE_SINHALA, 
                "සම්බන්ධතාවය අසාර්ථක විය: %s");
        addString(AddFriend.REGISTRATION_SUCCESSFUL, LOCALE_SINHALA, 
                "විශිෂ්ටයි! %s ස්මාර්ට් කණ්ණාඩි පද්ධතියේ සාර්ථකව ලියාපදිංචි කර ඇත. ඔවුන් දැන් ස්වයංක්‍රීයව හඳුනාගනු ලැබේ.");
        addString(AddFriend.FACE_REGISTRATION_SUCCESSFUL, LOCALE_SINHALA, 
                "මුහුණු ලියාපදිංචිය සාර්ථකයි! %s");
        addString(AddFriend.REGISTRATION_FAILED, LOCALE_SINHALA, 
                "ලියාපදිංචිය අසාර්ථක විය: %s");
        addString(AddFriend.SERVER_ERROR, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීමේ සේවාදායක දෝෂය: %s");
        addString(AddFriend.SERVER_READY, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීමේ සේවාදායකය සූදානම්. දැනට %d දෙනෙකු ලියාපදිංචි කර ඇත. දැන් ස්මාර්ට් කණ්ණාඩි වලට සම්බන්ධ වෙමින්.");
        addString(AddFriend.SERVER_NOT_RESPONDING, LOCALE_SINHALA, 
                "මුහුණු හඳුනාගැනීමේ සේවාදායකය ප්‍රතිචාර නොදක්වයි");
        addString(AddFriend.SPEECH_UNAVAILABLE, LOCALE_SINHALA, 
                "කථන හඳුනාගැනීම නොමැත.");
        addString(AddFriend.NETWORK_ERROR, LOCALE_SINHALA, 
                "ජාල දෝෂයකි. කරුණාකර ඔබේ සම්බන්ධතාවය පරීක්ෂා කර නැවත උත්සාහ කරන්න.");
        addString(Settings.BACK_TO_MAIN, LOCALE_SINHALA, "ප්‍රධාන මෙනුවට ආපසු යමින්");
        addString(Settings.SCREEN_OPEN, LOCALE_SINHALA, "සැකසුම් තිරය විවෘත කර ඇත. භාෂා මනාපය තෝරන්න.");
        addString(Settings.BACK_BUTTON_DESC, LOCALE_SINHALA, "ආපසු බොත්තම. ප්‍රධාන මෙනුවට ආපසු යමින්.");
        addString(AddFriend.SPEECH_UNAVAILABLE, LOCALE_SINHALA,
                "කථන හඳුනාගැනීම නොමැත. කරුණාකර නාවිගේෂන් සඳහා බොත්තම් භාවිතා කරන්න.");

        addString(Settings.BACK_BUTTON_DESC, LOCALE_SINHALA,
                "ආපසු බොත්තම. ප්‍රධාන මෙනුවට ආපසු යන්න තට්ටු කරන්න.");
        addString(Main.STOP_OBSTACLES_NEAR, LOCALE_SINHALA,
                "නවතන්න ඉදිරියෙන් බාධකයක්");


    }

    private static void addString(String stringId, Locale locale, String value) {
        Map<Locale, String> localizations = STRING_RESOURCES.computeIfAbsent(stringId, k -> new HashMap<>());
        localizations.put(locale, value);
    }
}