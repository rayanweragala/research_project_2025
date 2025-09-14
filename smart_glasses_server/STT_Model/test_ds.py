import json
import os
import librosa
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration (should match training script)
SAMPLE_RATE = 16000
MAX_AUDIO_LENGTH = 5000    # Max audio duration in ms (5 seconds)
N_MFCC = 13

class SinhalaSSTTester:
    def __init__(self, model_path='sinhala_stt_model.h5', vocab_path='vocabulary.json'):
        """Initialize the tester with trained model and vocabulary"""
        self.model_path = model_path
        self.vocab_path = vocab_path
        self.model = None
        self.char_to_num = None
        self.num_to_char = None
        
        self.load_model_and_vocab()
    
    def load_model_and_vocab(self):
        """Load the trained model and vocabulary"""
        try:
            # Load vocabulary
            if not os.path.exists(self.vocab_path):
                print(f"Error: Vocabulary file {self.vocab_path} not found!")
                return False
                
            with open(self.vocab_path, 'r', encoding='utf-8') as f:
                vocab_data = json.load(f)
                self.char_to_num = vocab_data['char_to_num']
                # Convert string keys back to integers for num_to_char
                self.num_to_char = {int(k): v for k, v in vocab_data['num_to_char'].items()}
            
            print(f"Loaded vocabulary with {len(self.char_to_num)} characters")
            
            # Load model
            if not os.path.exists(self.model_path):
                print(f"Error: Model file {self.model_path} not found!")
                return False
            
            # Custom CTC loss function (needed for loading)
            def ctc_loss_func(y_true, y_pred):
                batch_len = tf.cast(tf.shape(y_true)[0], dtype="int64")
                input_length = tf.cast(tf.shape(y_pred)[1], dtype="int64")
                label_length = tf.cast(tf.shape(y_true)[1], dtype="int64")
                
                input_length = input_length * tf.ones(shape=(batch_len, 1), dtype="int64")
                label_length = label_length * tf.ones(shape=(batch_len, 1), dtype="int64")
                
                loss = tf.keras.backend.ctc_batch_cost(y_true, y_pred, input_length, label_length)
                return loss
            
            self.model = load_model(self.model_path, custom_objects={'ctc_loss_func': ctc_loss_func})
            print("Model loaded successfully!")
            return True
            
        except Exception as e:
            print(f"Error loading model or vocabulary: {e}")
            return False
    
    def extract_mfcc(self, audio_path, max_pad_len=100):
        """Extract MFCC features from audio file (same as training script)"""
        try:
            print(f"Processing audio file: {audio_path}")
            y, sr = librosa.load(audio_path, sr=SAMPLE_RATE)
            
            print(f"Original audio: {len(y)} samples, {len(y)/sr:.2f} seconds")
            
            # Ensure audio is 5 seconds (pad/trim)
            max_len = int(SAMPLE_RATE * (MAX_AUDIO_LENGTH / 1000))
            if len(y) > max_len:
                y = y[:max_len]
                print("Audio trimmed to 5 seconds")
            else:
                y = np.pad(y, (0, max(0, max_len - len(y))), 'constant')
                print("Audio padded to 5 seconds")
            
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
            mfccs = np.transpose(mfccs)  # Shape: (time, n_mfcc)
            
            # Pad/trim to fixed timesteps
            if mfccs.shape[0] > max_pad_len:
                mfccs = mfccs[:max_pad_len, :]
            else:
                pad_width = [(0, max_pad_len - mfccs.shape[0]), (0, 0)]
                mfccs = np.pad(mfccs, pad_width, mode='constant')
            
            print(f"MFCC features shape: {mfccs.shape}")
            return mfccs
            
        except Exception as e:
            print(f"Error extracting MFCC from {audio_path}: {e}")
            return None
    
    def decode_prediction(self, prediction):
        """Decode CTC prediction to text"""
        try:
            # Get the predicted sequence
            pred_indices = tf.argmax(prediction, axis=-1)
            
            # Convert to numpy if tensor
            if hasattr(pred_indices, 'numpy'):
                pred_indices = pred_indices.numpy()
            
            # Decode sequence
            decoded_chars = []
            prev_char = -1
            
            for idx in pred_indices[0]:  # Take first (and only) sequence
                # CTC decoding: remove blanks (0) and repeated characters
                if idx != 0 and idx != prev_char:
                    if idx in self.num_to_char:
                        decoded_chars.append(self.num_to_char[idx])
                prev_char = idx
            
            return ''.join(decoded_chars)
            
        except Exception as e:
            print(f"Error decoding prediction: {e}")
            return ""
    
    def predict_audio(self, audio_path):
        """Predict text from audio file"""
        if self.model is None or self.num_to_char is None:
            print("Model or vocabulary not loaded!")
            return ""
        
        # Extract features
        mfcc = self.extract_mfcc(audio_path)
        if mfcc is None:
            return ""
        
        # Prepare input (add batch dimension)
        input_data = np.expand_dims(mfcc, axis=0)
        print(f"Input shape for prediction: {input_data.shape}")
        
        try:
            # Make prediction
            print("Making prediction...")
            prediction = self.model.predict(input_data, verbose=0)
            print(f"Prediction shape: {prediction.shape}")
            
            # Decode prediction
            decoded_text = self.decode_prediction(prediction)
            
            return decoded_text
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            return ""
    
    def save_result_to_json(self, audio_path, predicted_text, output_dir="results"):
        """Save the prediction result to a JSON file"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Get audio filename without extension
            audio_filename = os.path.splitext(os.path.basename(audio_path))[0]
            
            # Create JSON filename
            json_filename = f"{audio_filename}_result.json"
            json_path = os.path.join(output_dir, json_filename)
            
            # Prepare result data
            result_data = {
                "audio_file": os.path.basename(audio_path),
                "audio_path": audio_path,
                "predicted_text": predicted_text,
                "timestamp": datetime.now().isoformat(),
                "model_path": self.model_path,
                "vocabulary_path": self.vocab_path,
                "success": bool(predicted_text.strip())
            }
            
            # Save to JSON file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"Result saved to: {json_path}")
            return json_path
            
        except Exception as e:
            print(f"Error saving result to JSON: {e}")
            return None

def main():
    """Main testing function"""
    print("Sinhala Speech-to-Text Model Tester")
    print("=" * 40)
    
    # Initialize tester
    tester = SinhalaSSTTester()
    
    if tester.model is None:
        print("Failed to initialize tester. Please check model and vocabulary files.")
        return
    
    # HARDCODED AUDIO PATH - CHANGE THIS TO YOUR AUDIO FILE
    audio_path = "converted.wav"  # PUT YOUR AUDIO FILE PATH HERE
    
    if not os.path.exists(audio_path):
        print(f"Error: Audio file '{audio_path}' not found!")
        print("Please update the audio_path variable in the code with your actual file path")
        return
    
    print(f"\nTesting with: {audio_path}")
    print("-" * 30)
    
    # Predict
    result = tester.predict_audio(audio_path)
    
    print(f"\nPredicted text: '{result}'")
    
    # Save result to JSON file
    json_path = tester.save_result_to_json(audio_path, result)
    
    if not result:
        print("No text was recognized. This could be due to:")
        print("- Audio quality issues")
        print("- Language mismatch (model trained for Sinhala)")
        print("- Model needs more training")
        print("- Audio format incompatibility")
    
    if json_path:
        print(f"\nResult has been saved to JSON file: {json_path}")

def batch_process(audio_folder, output_dir="batch_results"):
    """Process multiple audio files in a folder"""
    print("Batch Processing Mode")
    print("=" * 40)
    
    # Initialize tester
    tester = SinhalaSSTTester()
    
    if tester.model is None:
        print("Failed to initialize tester. Please check model and vocabulary files.")
        return
    
    # Get all audio files in the folder
    audio_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
    audio_files = []
    
    if os.path.exists(audio_folder):
        for file in os.listdir(audio_folder):
            if any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(os.path.join(audio_folder, file))
    
    if not audio_files:
        print(f"No audio files found in {audio_folder}")
        return
    
    print(f"Found {len(audio_files)} audio files to process")
    
    # Process each file
    results = []
    for i, audio_path in enumerate(audio_files, 1):
        print(f"\nProcessing {i}/{len(audio_files)}: {os.path.basename(audio_path)}")
        print("-" * 50)
        
        # Predict
        result = tester.predict_audio(audio_path)
        
        # Save individual result
        json_path = tester.save_result_to_json(audio_path, result, output_dir)
        
        results.append({
            "audio_file": os.path.basename(audio_path),
            "predicted_text": result,
            "json_file": os.path.basename(json_path) if json_path else None
        })
        
        print(f"Result: '{result}'")
    
    # Save batch summary
    try:
        summary_path = os.path.join(output_dir, "batch_summary.json")
        summary_data = {
            "processed_files": len(audio_files),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nBatch summary saved to: {summary_path}")
    except Exception as e:
        print(f"Error saving batch summary: {e}")

if __name__ == "__main__":
    # Check if required files exist
    required_files = ['sinhala_stt_model.h5', 'vocabulary.json']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("Missing required files:")
        for f in missing_files:
            print(f"  - {f}")
        print("\nPlease run the training script first to generate these files.")
    else:
        # Choose processing mode
        print("Choose processing mode:")
        print("1. Single file (default)")
        print("2. Batch process folder")
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            folder_path = input("Enter audio folder path: ").strip()
            if not folder_path:
                folder_path = "audio_files"  # Default folder
            batch_process(folder_path)
        else:
            main()