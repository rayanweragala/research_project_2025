package com.research.blindassistant;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * StringResources class to centralize all speech strings used in the application.
 * This allows for easy translation and management of text-to-speech content.
 */
public class StringResources {
    
    // Default language is English
    private static Locale currentLocale = Locale.US;
    
    // Supported languages
    public static final Locale LOCALE_ENGLISH = Locale.US;
    public static final Locale LOCALE_SPANISH = new Locale("es", "ES");
    public static final Locale LOCALE_FRENCH = Locale.FRANCE;
    
    /**
     * Set the current locale for string resources
     * @param locale The locale to use
     */
    public static void setLocale(Locale locale) {
        currentLocale = locale;
    }
    
    /**
     * Get the current locale
     * @return The current locale
     */
    public static Locale getCurrentLocale() {
        return currentLocale;
    }
    
    /**
     * Get a string resource in the current locale
     * @param stringId The string identifier
     * @return The localized string
     */
    public static String getString(String stringId) {
        return getLocalizedString(stringId, currentLocale);
    }
    
    /**
     * Get a string resource in a specific locale
     * @param stringId The string identifier
     * @param locale The locale to use
     * @return The localized string
     */
    public static String getLocalizedString(String stringId, Locale locale) {
        Map<Locale, String> localizations = STRING_RESOURCES.get(stringId);
        if (localizations != null) {
            String localizedString = localizations.get(locale);
            if (localizedString != null) {
                return localizedString;
            }
            // Fallback to English if the requested locale is not available
            return localizations.get(LOCALE_ENGLISH);
        }
        return stringId; // Return the ID if string not found
    }
    
    // String identifiers for MainActivity
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
        
        // Error messages
        public static final String ERROR_AUDIO = "main_error_audio";
        public static final String ERROR_CLIENT = "main_error_client";
        public static final String ERROR_INSUFFICIENT_PERMISSIONS = "main_error_insufficient_permissions";
        public static final String ERROR_NETWORK = "main_error_network";
        public static final String ERROR_NETWORK_TIMEOUT = "main_error_network_timeout";
        public static final String ERROR_NO_MATCH = "main_error_no_match";
        public static final String ERROR_RECOGNIZER_BUSY = "main_error_recognizer_busy";
        public static final String ERROR_SERVER = "main_error_server";
        public static final String ERROR_SPEECH_TIMEOUT = "main_error_speech_timeout";
    }
    
    // String identifiers for EnhancedFaceRecognitionActivity
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
    
    // String identifiers for AddFriendActivity
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
    
    // Map of all string resources with their localizations
    private static final Map<String, Map<Locale, String>> STRING_RESOURCES = new HashMap<>();
    
    static {
        // Initialize all string resources
        
        // MainActivity strings
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
        
        // Error messages
        addString(Main.ERROR_AUDIO, LOCALE_ENGLISH, "Audio recording error");
        addString(Main.ERROR_CLIENT, LOCALE_ENGLISH, "Client side error");
        addString(Main.ERROR_INSUFFICIENT_PERMISSIONS, LOCALE_ENGLISH, "Insufficient permissions");
        addString(Main.ERROR_NETWORK, LOCALE_ENGLISH, "Network error");
        addString(Main.ERROR_NETWORK_TIMEOUT, LOCALE_ENGLISH, "Network timeout");
        addString(Main.ERROR_NO_MATCH, LOCALE_ENGLISH, "No speech match found. Try again.");
        addString(Main.ERROR_RECOGNIZER_BUSY, LOCALE_ENGLISH, "Speech recognizer busy");
        addString(Main.ERROR_SERVER, LOCALE_ENGLISH, "Server error");
        addString(Main.ERROR_SPEECH_TIMEOUT, LOCALE_ENGLISH, "Speech timeout");
        
        // EnhancedFaceRecognitionActivity strings
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
        
        // AddFriendActivity strings
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
        
        // Add Spanish translations (example for a few strings)
        addString(Main.ASSISTANT_READY, LOCALE_SPANISH, 
                "Asistente listo. Diga comandos como cara, voz, navegación o configuración. O toque cualquier botón.");
        addString(Main.FACE_RECOGNITION_STARTING, LOCALE_SPANISH, 
                "Iniciando reconocimiento facial");
        
        // Add French translations (example for a few strings)
        addString(Main.ASSISTANT_READY, LOCALE_FRENCH, 
                "Assistant prêt. Dites des commandes comme visage, voix, navigation ou paramètres. Ou appuyez sur n'importe quel bouton.");
        addString(Main.FACE_RECOGNITION_STARTING, LOCALE_FRENCH, 
                "Démarrage de la reconnaissance faciale");
    }
    
    /**
     * Helper method to add a string resource with localization
     * @param stringId The string identifier
     * @param locale The locale
     * @param value The localized string value
     */
    private static void addString(String stringId, Locale locale, String value) {
        Map<Locale, String> localizations = STRING_RESOURCES.computeIfAbsent(stringId, k -> new HashMap<>());
        localizations.put(locale, value);
    }
}