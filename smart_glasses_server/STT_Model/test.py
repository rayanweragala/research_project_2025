import tensorflow as tf
import numpy as np
import json
import librosa
import os
from datetime import datetime

class SinhalaSpeechTranscriber:
    def __init__(self, model_path):
        """
        Initialize the Sinhala Speech-to-Text transcriber
        
        Args:
            model_path (str): Path to the .tflite model file
        """
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.load_model()
    
    def load_model(self):
        """Load the TensorFlow Lite model"""
        try:
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            print(f"Model loaded successfully from {self.model_path}")
            print(f"Input shape: {self.input_details[0]['shape']}")
            print(f"Output shape: {self.output_details[0]['shape']}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def preprocess_audio_approach(self, audio_path, approach="mfcc_mean", target_sr=16000):
        """
        Preprocess audio using a specific approach
        
        Args:
            audio_path (str): Path to the audio file
            approach (str): Preprocessing approach to use
            target_sr (int): Target sample rate
            
        Returns:
            np.array: Preprocessed audio features
        """
        try:
            # Load audio file
            audio, sr = librosa.load(audio_path, sr=target_sr)
            
            print(f"Audio loaded: duration={len(audio)/sr:.2f}s, sample_rate={sr}, shape={audio.shape}")
            print(f"Audio stats: min={np.min(audio):.4f}, max={np.max(audio):.4f}, mean={np.mean(audio):.4f}, std={np.std(audio):.4f}")
            
            # Check if audio is too quiet
            if np.max(np.abs(audio)) < 0.01:
                print("WARNING: Audio seems very quiet, normalizing...")
                audio = audio / np.max(np.abs(audio)) * 0.5
            
            # Get the expected input shape from the model
            input_shape = self.input_details[0]['shape']
            print(f"Expected input shape: {input_shape}")
            print(f"Using approach: {approach}")
            
            if approach == "mfcc_mean":
                # MFCC features averaged to single value per frame
                hop_length = max(1, len(audio) // (input_shape[1] - 1))
                
                mfcc = librosa.feature.mfcc(
                    y=audio, 
                    sr=sr, 
                    n_mfcc=13,
                    hop_length=hop_length,
                    n_fft=min(512, len(audio))
                )
                
                # Take mean across MFCC coefficients
                features = np.mean(mfcc, axis=0)
                
            elif approach == "mel_mean":
                # Mel spectrogram averaged to single value per frame
                hop_length = max(1, len(audio) // (input_shape[1] - 1))
                    
                mel_spec = librosa.feature.melspectrogram(
                    y=audio,
                    sr=sr,
                    n_mels=13,
                    hop_length=hop_length,
                    n_fft=min(512, len(audio))
                )
                
                # Take mean across mel bands
                features = np.mean(mel_spec, axis=0)
                
            elif approach == "rms_energy":
                # RMS energy per frame
                hop_length = max(1, len(audio) // (input_shape[1] - 1))
                    
                rms = librosa.feature.rms(
                    y=audio,
                    hop_length=hop_length,
                    frame_length=min(512, len(audio))
                )[0]
                
                features = rms
                
            elif approach == "zero_crossing_rate":
                # Zero crossing rate per frame
                hop_length = max(1, len(audio) // (input_shape[1] - 1))
                    
                zcr = librosa.feature.zero_crossing_rate(
                    y=audio,
                    hop_length=hop_length,
                    frame_length=min(512, len(audio))
                )[0]
                
                features = zcr
                
            elif approach == "raw_audio":
                # Direct raw audio (downsampled to fit timesteps)
                target_length = input_shape[1]
                if len(audio) > target_length:
                    # Downsample by taking every nth sample
                    step = len(audio) // target_length
                    features = audio[::step][:target_length]
                else:
                    # Pad with zeros
                    features = np.pad(audio, (0, target_length - len(audio)), 'constant')
            
            else:
                raise ValueError(f"Unknown approach: {approach}")
            
            # Ensure correct length
            if len(features) > input_shape[1]:
                features = features[:input_shape[1]]
            elif len(features) < input_shape[1]:
                features = np.pad(features, (0, input_shape[1] - len(features)), 'constant')
            
            # Add batch dimension
            features = features[np.newaxis, :]
            
            print(f"Features shape: {features.shape}")
            print(f"Features stats: min={np.min(features):.4f}, max={np.max(features):.4f}, mean={np.mean(features):.4f}")
            
            return features.astype(np.float32)
            
        except Exception as e:
            print(f"Error preprocessing audio with {approach}: {e}")
            raise
    
    def decode_prediction(self, prediction):
        """
        Decode the model prediction to text
        
        Args:
            prediction (np.array): Model output
            
        Returns:
            str: Decoded text
        """
        print(f"Prediction shape: {prediction.shape}")
        print(f"Prediction dtype: {prediction.dtype}")
        print(f"Prediction min/max: {np.min(prediction):.4f}/{np.max(prediction):.4f}")
        
        # Common Sinhala characters for speech-to-text models
        # You'll need to replace this with your actual character mapping
        sinhala_chars = [
            ' ', 'අ', 'ආ', 'ඇ', 'ඈ', 'ඉ', 'ඊ', 'උ', 'ඌ', 'ඍ', 'ඎ', 'ඏ', 'ඐ', 'එ', 'ඒ', 'ඓ', 'ඔ', 'ඕ', 'ඖ',
            'ක', 'ඛ', 'ග', 'ඝ', 'ඞ', 'ඟ', 'ච', 'ඡ', 'ජ', 'ඣ', 'ඤ', 'ඥ', 'ට', 'ඨ', 'ඩ', 'ඪ', 'ණ', 'ඬ', 'ත', 'ථ',
            'ද', 'ධ', 'න', 'ඳ', 'ප', 'ඵ', 'බ', 'භ', 'ම', 'ඹ', 'ය', 'ර', 'ල', 'ව', 'ශ', 'ෂ', 'ස', 'හ', 'ළ', 'ෆ',
            'ං', 'ඃ', 'ා', 'ැ', 'ෑ', 'ි', 'ී', 'ු', 'ූ', 'ෘ', 'ෙ', 'ේ', 'ෛ', 'ො', 'ෝ', 'ෞ', 'ෟ', 'ෲ', 'ෳ'
        ]
        
        try:
            # Handle different output formats
            if len(prediction.shape) == 3:  # (batch, time, vocab_size)
                print(f"Processing 3D output: batch={prediction.shape[0]}, time={prediction.shape[1]}, vocab={prediction.shape[2]}")
                
                # Get the most likely character at each time step
                predicted_ids = np.argmax(prediction[0], axis=1)
                print(f"Predicted IDs: {predicted_ids[:20]}...")  # Show first 20 IDs
                
                # CTC decoding - remove consecutive duplicates and blanks
                decoded_sequence = []
                prev_id = -1
                for char_id in predicted_ids:
                    if char_id != prev_id and char_id != 0:  # Assuming 0 is blank token
                        decoded_sequence.append(char_id)
                    prev_id = char_id
                
                print(f"Decoded sequence length: {len(decoded_sequence)}")
                print(f"Decoded IDs: {decoded_sequence}")
                
                # Convert to text using character mapping
                text = ""
                for char_id in decoded_sequence:
                    if 0 <= char_id < len(sinhala_chars):
                        text += sinhala_chars[char_id]
                    else:
                        text += f"[UNK{char_id}]"  # Unknown character
                
            elif len(prediction.shape) == 2:  # (batch, vocab_size) - single prediction
                print(f"Processing 2D output: batch={prediction.shape[0]}, vocab={prediction.shape[1]}")
                
                # Get top predictions
                predicted_ids = np.argsort(prediction[0])[-10:][::-1]  # Top 10 predictions
                print(f"Top 10 predicted IDs: {predicted_ids}")
                print(f"Top 10 probabilities: {prediction[0][predicted_ids]}")
                
                # Use the most likely prediction
                best_id = predicted_ids[0]
                if 0 <= best_id < len(sinhala_chars):
                    text = sinhala_chars[best_id]
                else:
                    text = f"[UNK{best_id}]"
                
            elif len(prediction.shape) == 1:  # (vocab_size,) - single timestep
                print(f"Processing 1D output: vocab={prediction.shape[0]}")
                
                # Get the most likely character
                predicted_id = np.argmax(prediction)
                print(f"Predicted ID: {predicted_id}, Probability: {prediction[predicted_id]:.4f}")
                
                if 0 <= predicted_id < len(sinhala_chars):
                    text = sinhala_chars[predicted_id]
                else:
                    text = f"[UNK{predicted_id}]"
                    
            else:
                text = f"Unsupported output shape: {prediction.shape}"
                
        except Exception as e:
            print(f"Error in decoding: {e}")
            text = f"Decoding error: {str(e)}"
        
        print(f"Final decoded text: '{text}'")
        return text
    
    def test_multiple_preprocessing(self, audio_path):
        """
        Test multiple preprocessing approaches to find the best one
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            dict: Results from different preprocessing approaches
        """
        approaches = ["mfcc_mean", "mel_mean", "rms_energy", "zero_crossing_rate", "raw_audio"]
        results = {}
        
        for approach in approaches:
            try:
                print(f"\n=== Testing {approach} ===")
                
                # Preprocess audio with this approach
                features = self.preprocess_audio_approach(audio_path, approach)
                
                # Run inference
                self.interpreter.set_tensor(self.input_details[0]['index'], features)
                self.interpreter.invoke()
                output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
                
                # Analyze output
                predicted_ids = np.argmax(output_data[0], axis=1)
                unique_ids = np.unique(predicted_ids)
                non_zero_count = np.sum(predicted_ids != 0)
                
                print(f"Unique predicted IDs: {unique_ids}")
                print(f"Non-zero predictions: {non_zero_count}/{len(predicted_ids)}")
                
                # Try to decode
                transcription = self.decode_prediction(output_data)
                
                results[approach] = {
                    'transcription': transcription,
                    'unique_ids': unique_ids.tolist(),
                    'non_zero_count': non_zero_count,
                    'total_predictions': len(predicted_ids)
                }
                
            except Exception as e:
                print(f"Error with {approach}: {e}")
                results[approach] = {'error': str(e)}
        
        return results
    
    def transcribe_audio(self, audio_path, approach="mfcc_mean"):
        """
        Transcribe audio file
        
        Args:
            audio_path (str): Path to the audio file
            approach (str): Preprocessing approach to use
            
        Returns:
            dict: Transcription results
        """
        try:
            # Preprocess audio
            features = self.preprocess_audio_approach(audio_path, approach)
            
            # Set input tensor
            self.interpreter.set_tensor(self.input_details[0]['index'], features)
            
            # Run inference
            self.interpreter.invoke()
            
            # Get output
            output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            # Decode prediction
            transcription = self.decode_prediction(output_data)
            
            # Get audio file info
            audio_duration = librosa.get_duration(path=audio_path)
            
            result = {
                'audio_file': os.path.basename(audio_path),
                'audio_path': audio_path,
                'transcription': transcription,
                'audio_duration_seconds': round(audio_duration, 2),
                'model_used': os.path.basename(self.model_path),
                'preprocessing_approach': approach,
                'timestamp': datetime.now().isoformat(),
                'confidence': None  # Add confidence score if available from your model
            }
            
            return result
            
        except Exception as e:
            print(f"Error during transcription: {e}")
            raise

def comprehensive_test():
    """Test all preprocessing approaches to find the best one"""
    
    # Configuration
    MODEL_PATH = "sinhala_stt_model.tflite"
    AUDIO_FILE = "converted.wav"
    
    # Check if files exist
    if not os.path.exists(MODEL_PATH):
        print(f"Model file not found: {MODEL_PATH}")
        return
    
    if not os.path.exists(AUDIO_FILE):
        print(f"Audio file not found: {AUDIO_FILE}")
        return
    
    try:
        # Initialize transcriber
        transcriber = SinhalaSpeechTranscriber(MODEL_PATH)
        
        # Test all preprocessing approaches
        print("=== TESTING ALL PREPROCESSING APPROACHES ===")
        results = transcriber.test_multiple_preprocessing(AUDIO_FILE)
        
        # Print results
        print("\n=== RESULTS SUMMARY ===")
        for approach, result in results.items():
            if 'error' in result:
                print(f"{approach}: ERROR - {result['error']}")
            else:
                print(f"{approach}:")
                print(f"  Transcription: '{result['transcription']}'")
                print(f"  Non-zero predictions: {result['non_zero_count']}/{result['total_predictions']}")
                print(f"  Unique IDs: {result['unique_ids']}")
                print()
        
        # Find best approach (most non-zero predictions)
        best_approach = None
        best_score = 0
        for approach, result in results.items():
            if 'non_zero_count' in result and result['non_zero_count'] > best_score:
                best_score = result['non_zero_count']
                best_approach = approach
        
        if best_approach:
            print(f"=== BEST APPROACH: {best_approach} ===")
            print(f"Non-zero predictions: {best_score}")
            print(f"Transcription: '{results[best_approach]['transcription']}'")
            
            # Run final transcription with best approach
            final_result = transcriber.transcribe_audio(AUDIO_FILE, best_approach)
            
            # Save final result
            with open("final_transcription_result.json", 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=2, ensure_ascii=False)
            
            print(f"Final result saved to: final_transcription_result.json")
        
        # Save comprehensive results
        with open("comprehensive_test_results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("Comprehensive test results saved to: comprehensive_test_results.json")
        
    except Exception as e:
        print(f"Error during comprehensive test: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function for regular transcription"""
    
    # Configuration
    MODEL_PATH = "sinhala_stt_model.tflite"
    AUDIO_FILE = "converted.wav"
    OUTPUT_JSON = "transcription_results.json"
    APPROACH = "mfcc_mean"  # Change this based on comprehensive test results
    
    # Check if files exist
    if not os.path.exists(MODEL_PATH):
        print(f"Model file not found: {MODEL_PATH}")
        return
    
    if not os.path.exists(AUDIO_FILE):
        print(f"Audio file not found: {AUDIO_FILE}")
        return
    
    try:
        # Initialize transcriber
        transcriber = SinhalaSpeechTranscriber(MODEL_PATH)
        
        # Transcribe audio
        print(f"Transcribing {AUDIO_FILE} using {APPROACH} approach...")
        result = transcriber.transcribe_audio(AUDIO_FILE, APPROACH)
        
        # Save results to JSON
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Transcription completed!")
        print(f"Results saved to: {OUTPUT_JSON}")
        print(f"Transcription: {result['transcription']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Run comprehensive test to find best preprocessing approach
    comprehensive_test()