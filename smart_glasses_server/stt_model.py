# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import librosa
import numpy as np
import base64
import json
import threading
import time
import logging
import os
import tempfile
import io
import wave
import socket
from datetime import datetime
import difflib
import re
from collections import Counter
from queue import Queue

# For microphone recording
import pyaudio
import threading

# Your model setup
MODEL_PATH = "../whisper-sinhala"
DEVICE = "cpu"
LANGUAGE = "si"

# Model imports
try:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    CUSTOM_MODEL_AVAILABLE = True
    print(f"✅ Transformers available. Model path: {MODEL_PATH}")
except ImportError as e:
    CUSTOM_MODEL_AVAILABLE = False
    print(f"❌ Transformers not available: {e}")

# Fallback imports
try:
    import speech_recognition as sr
    SPEECHRECOGNITION_AVAILABLE = True
except ImportError:
    SPEECHRECOGNITION_AVAILABLE = False

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

class AudioProcessor:
    """Handle audio preprocessing and format conversion"""
    
    @staticmethod
    def convert_to_target_format(audio_data, sample_rate, target_sr=16000):
        """Convert audio to 16kHz mono WAV format"""
        try:
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = librosa.to_mono(audio_data)
            
            # Resample to target sample rate
            if sample_rate != target_sr:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)
            
            # Normalize audio
            audio_data = librosa.util.normalize(audio_data)
            
            return audio_data, target_sr
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            return None, None
    
    @staticmethod
    def save_as_wav(audio_data, sample_rate, output_path):
        """Save audio data as WAV file"""
        try:
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(output_path, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            return True
        except Exception as e:
            print(f"Error saving WAV file: {e}")
            return False
    
    @staticmethod
    def load_audio_file(file_path):
        """Load audio file using librosa"""
        try:
            audio_data, sample_rate = librosa.load(file_path, sr=None)
            return audio_data, sample_rate
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return None, None

class MicrophoneRecorder:
    """Handle microphone recording with proper thread management"""
    
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.is_recording = False
        self.audio_queue = Queue()
        self.pyaudio_instance = None
        self.stream = None
        self.recording_thread = None
        self.audio_format = pyaudio.paInt16
        
    def _recording_worker(self):
        """Worker thread for continuous recording"""
        while self.is_recording and self.stream:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                if data:
                    self.audio_queue.put(data)
            except Exception as e:
                print(f"Error in recording worker: {e}")
                break
    
    def start_recording(self):
        """Start recording from microphone"""
        try:
            if self.is_recording:
                print("Recording already in progress")
                return False
                
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Find and configure input device
            try:
                device_info = self.pyaudio_instance.get_default_input_device_info()
                device_index = device_info['index']
                print(f"Using microphone: {device_info['name']}")
            except:
                device_index = None
                print("Using system default microphone")
            
            # Try different audio configurations
            configs_to_try = [
                # (format, channels, sample_rate)
                (pyaudio.paInt16, self.channels, self.sample_rate),
                (pyaudio.paInt16, 1, 44100),
                (pyaudio.paInt16, 1, 22050),
                (pyaudio.paFloat32, self.channels, self.sample_rate),
            ]
            
            stream_opened = False
            for audio_format, channels, rate in configs_to_try:
                try:
                    self.stream = self.pyaudio_instance.open(
                        format=audio_format,
                        channels=channels,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=self.chunk_size,
                        stream_callback=None
                    )
                    
                    # Update instance variables with working config
                    self.channels = channels
                    self.sample_rate = rate
                    self.audio_format = audio_format
                    
                    print(f"Audio stream opened: {rate}Hz, {channels}ch, format={audio_format}")
                    stream_opened = True
                    break
                    
                except Exception as e:
                    print(f"Failed to open stream with config {audio_format}, {channels}, {rate}: {e}")
                    continue
            
            if not stream_opened:
                raise Exception("Could not open audio stream with any configuration")
            
            # Clear the queue and start recording
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            self.is_recording = True
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
            self.recording_thread.start()
            
            print("Microphone recording started successfully")
            return True
            
        except Exception as e:
            print(f"Error starting microphone recording: {e}")
            self._cleanup()
            return False
    
    def stop_recording(self):
        """Stop recording and return audio data"""
        try:
            if not self.is_recording:
                print("No recording in progress")
                return None, None
            
            print("Stopping recording...")
            self.is_recording = False
            
            # Wait for recording thread to finish
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            
            # Collect all audio data from queue
            audio_chunks = []
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                audio_chunks.append(chunk)
            
            self._cleanup()
            
            if not audio_chunks:
                print("No audio data collected")
                return None, None
            
            # Convert to numpy array
            audio_bytes = b''.join(audio_chunks)
            
            if self.audio_format == pyaudio.paInt16:
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                audio_array = audio_array / 32768.0  # Normalize to [-1, 1]
            elif self.audio_format == pyaudio.paFloat32:
                audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            else:
                raise Exception(f"Unsupported audio format: {self.audio_format}")
            
            duration = len(audio_array) / self.sample_rate
            print(f"Recording stopped. Duration: {duration:.2f} seconds, Samples: {len(audio_array)}")
            
            return audio_array, self.sample_rate
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            self._cleanup()
            return None, None
    
    def _cleanup(self):
        """Clean up audio resources"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
                self.pyaudio_instance = None
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def is_recording_active(self):
        """Check if recording is currently active"""
        return self.is_recording and self.stream and self.stream.is_active()
    
    def get_recording_info(self):
        """Get current recording configuration"""
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'chunk_size': self.chunk_size,
            'is_recording': self.is_recording,
            'format': getattr(self, 'audio_format', None),
            'queue_size': self.audio_queue.qsize() if hasattr(self, 'audio_queue') else 0
        }

class AccuracyCalculator:
    """Calculate transcription accuracy metrics"""
    
    @staticmethod
    def calculate_word_accuracy(reference, hypothesis):
        """Calculate Word Error Rate (WER) and word accuracy"""
        ref_words = AccuracyCalculator.clean_text(reference).split()
        hyp_words = AccuracyCalculator.clean_text(hypothesis).split()
        
        # Calculate edit distance
        d = np.zeros((len(ref_words) + 1, len(hyp_words) + 1))
        
        for i in range(len(ref_words) + 1):
            d[i][0] = i
        for j in range(len(hyp_words) + 1):
            d[0][j] = j
            
        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(hyp_words) + 1):
                if ref_words[i-1] == hyp_words[j-1]:
                    cost = 0
                else:
                    cost = 1
                    
                d[i][j] = min(
                    d[i-1][j] + 1,      # deletion
                    d[i][j-1] + 1,      # insertion
                    d[i-1][j-1] + cost  # substitution
                )
        
        edit_distance = d[len(ref_words)][len(hyp_words)]
        
        if len(ref_words) == 0:
            wer = 0 if len(hyp_words) == 0 else 1
        else:
            wer = edit_distance / len(ref_words)
        
        word_accuracy = max(0, 1 - wer)
        
        return {
            'word_accuracy': word_accuracy * 100,
            'wer': wer * 100,
            'edit_distance': int(edit_distance),
            'reference_word_count': len(ref_words),
            'hypothesis_word_count': len(hyp_words)
        }
    
    @staticmethod
    def calculate_character_accuracy(reference, hypothesis):
        """Calculate Character Error Rate (CER)"""
        ref_chars = list(AccuracyCalculator.clean_text(reference, keep_spaces=True))
        hyp_chars = list(AccuracyCalculator.clean_text(hypothesis, keep_spaces=True))
        
        # Calculate edit distance for characters
        d = np.zeros((len(ref_chars) + 1, len(hyp_chars) + 1))
        
        for i in range(len(ref_chars) + 1):
            d[i][0] = i
        for j in range(len(hyp_chars) + 1):
            d[0][j] = j
            
        for i in range(1, len(ref_chars) + 1):
            for j in range(1, len(hyp_chars) + 1):
                if ref_chars[i-1] == hyp_chars[j-1]:
                    cost = 0
                else:
                    cost = 1
                    
                d[i][j] = min(
                    d[i-1][j] + 1,
                    d[i][j-1] + 1,
                    d[i-1][j-1] + cost
                )
        
        edit_distance = d[len(ref_chars)][len(hyp_chars)]
        
        if len(ref_chars) == 0:
            cer = 0 if len(hyp_chars) == 0 else 1
        else:
            cer = edit_distance / len(ref_chars)
        
        char_accuracy = max(0, 1 - cer)
        
        return {
            'char_accuracy': char_accuracy * 100,
            'cer': cer * 100,
            'char_edit_distance': int(edit_distance),
            'reference_char_count': len(ref_chars),
            'hypothesis_char_count': len(hyp_chars)
        }
    
    @staticmethod
    def clean_text(text, keep_spaces=False):
        """Clean text for comparison"""
        text = text.lower().strip()
        # Remove punctuation but keep spaces if requested
        if keep_spaces:
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        else:
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    @staticmethod
    def get_word_alignment(reference, hypothesis):
        """Get word-by-word alignment for detailed analysis"""
        ref_words = AccuracyCalculator.clean_text(reference).split()
        hyp_words = AccuracyCalculator.clean_text(hypothesis).split()
        
        matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
        alignment = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for k in range(i2 - i1):
                    alignment.append({
                        'reference': ref_words[i1 + k],
                        'hypothesis': hyp_words[j1 + k],
                        'status': 'correct'
                    })
            elif tag == 'replace':
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    ref_word = ref_words[i1 + k] if i1 + k < i2 else ''
                    hyp_word = hyp_words[j1 + k] if j1 + k < j2 else ''
                    alignment.append({
                        'reference': ref_word,
                        'hypothesis': hyp_word,
                        'status': 'substitution'
                    })
            elif tag == 'delete':
                for k in range(i2 - i1):
                    alignment.append({
                        'reference': ref_words[i1 + k],
                        'hypothesis': '',
                        'status': 'deletion'
                    })
            elif tag == 'insert':
                for k in range(j2 - j1):
                    alignment.append({
                        'reference': '',
                        'hypothesis': hyp_words[j1 + k],
                        'status': 'insertion'
                    })
        
        return alignment

class STTServer:
    """Main STT server class"""
    
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.microphone = MicrophoneRecorder()
        self.accuracy_calculator = AccuracyCalculator()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_transcriptions': 0,
            'failed_transcriptions': 0,
            'total_audio_duration': 0,
            'avg_processing_time': 0,
            'processing_times': [],
            'accuracy_scores': [],
            'start_time': time.time()
        }
        
        # Initialize STT model
        self.stt_model = None
        self.processor = None
        self.device = None
        self.init_stt_model()
    
    def init_stt_model(self):
        """Load your Whisper Sinhala model"""
        try:
            if not CUSTOM_MODEL_AVAILABLE:
                print("❌ Transformers not available")
                return False
            
            if not os.path.exists(MODEL_PATH):
                print(f"❌ Model path does not exist: {MODEL_PATH}")
                return False
            
            print(f"🔥 Loading Whisper Sinhala model from: {MODEL_PATH}")
            
            # Load your model
            self.device = torch.device(DEVICE)
            self.stt_model = WhisperForConditionalGeneration.from_pretrained(MODEL_PATH)
            self.processor = WhisperProcessor.from_pretrained(MODEL_PATH)
            self.stt_model.to(self.device)
            self.stt_model.eval()
            
            print(f"✅ Whisper Sinhala model loaded successfully")
            print(f"   Device: {DEVICE}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def transcribe_audio(self, audio_data, sample_rate):
        """Transcribe audio data using STT model"""
        start_time = time.time()
        
        try:
            # Save audio to temporary WAV file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            if not self.audio_processor.save_as_wav(audio_data, sample_rate, tmp_path):
                return None, "Error saving audio file"
            
            # Transcribe using your model
            transcription = self.perform_transcription(tmp_path, audio_data)
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            processing_time = time.time() - start_time
            
            # Update statistics
            self.stats['total_requests'] += 1
            if transcription:
                self.stats['successful_transcriptions'] += 1
            else:
                self.stats['failed_transcriptions'] += 1
            
            self.stats['total_audio_duration'] += len(audio_data) / sample_rate
            self.stats['processing_times'].append(processing_time)
            
            # Keep only last 100 processing times for average calculation
            if len(self.stats['processing_times']) > 100:
                self.stats['processing_times'] = self.stats['processing_times'][-100:]
            
            self.stats['avg_processing_time'] = np.mean(self.stats['processing_times'])
            
            return transcription, None
            
        except Exception as e:
            self.stats['total_requests'] += 1
            self.stats['failed_transcriptions'] += 1
            return None, str(e)
    
    def perform_transcription(self, audio_file_path, audio_data):
        """Transcribe with your Whisper Sinhala model"""
        try:
            if not self.stt_model:
                return "STT model not initialized"
            
            print(f"🎯 Transcribing with Whisper Sinhala")
            
            # Preprocess audio
            input_features = self.processor(
                audio_data, 
                sampling_rate=16000, 
                return_tensors="pt"
            ).input_features
            
            input_features = input_features.to(self.device)
            
            # Generate transcription
            with torch.no_grad():
                predicted_ids = self.stt_model.generate(
                    input_features,
                    language="si",  # Sinhala
                    task="transcribe"
                )
            
            # Decode the transcription
            transcription = self.processor.batch_decode(
                predicted_ids, 
                skip_special_tokens=True
            )[0]
            
            print(f"✅ Transcription: {transcription}")
            return transcription.strip()
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"

    def calculate_accuracy(self, reference_text, transcribed_text):
        """Calculate accuracy metrics"""
        try:
            word_metrics = self.accuracy_calculator.calculate_word_accuracy(reference_text, transcribed_text)
            char_metrics = self.accuracy_calculator.calculate_character_accuracy(reference_text, transcribed_text)
            alignment = self.accuracy_calculator.get_word_alignment(reference_text, transcribed_text)
            
            # Update accuracy statistics
            self.stats['accuracy_scores'].append(word_metrics['word_accuracy'])
            if len(self.stats['accuracy_scores']) > 100:
                self.stats['accuracy_scores'] = self.stats['accuracy_scores'][-100:]
            
            return {
                'word_metrics': word_metrics,
                'character_metrics': char_metrics,
                'alignment': alignment,
                'avg_word_accuracy': np.mean(self.stats['accuracy_scores']) if self.stats['accuracy_scores'] else 0
            }
        
        except Exception as e:
            print(f"Error calculating accuracy: {e}")
            return None

# Global STT server instance
stt_server = STTServer()

@app.route('/')
def index():
    """Serve the main STT interface"""
    return send_from_directory('.', 'stt_server_index.html')

@app.route('/stt/health', methods=['GET'])
def stt_health():
    """Check STT server health"""
    try:
        microphone_available = False
        try:
            p = pyaudio.PyAudio()
            microphone_available = p.get_default_input_device_info() is not None
            p.terminate()
        except:
            pass
        
        uptime = time.time() - stt_server.stats['start_time']
        
        response = {
            'status': 'healthy',
            'stt_model_available': stt_server.stt_model is not None,
            'stt_model_type': 'whisper-sinhala',
            'stt_model_path': MODEL_PATH,
            'microphone_available': microphone_available,
            'librosa_available': True,
            'uptime_seconds': uptime,
            'stats': stt_server.stats.copy(),
            'avg_accuracy': np.mean(stt_server.stats['accuracy_scores']) if stt_server.stats['accuracy_scores'] else 0
        }
        
        # Remove processing times list from response to reduce size
        if 'processing_times' in response['stats']:
            del response['stats']['processing_times']
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/stt/transcribe_file', methods=['POST'])
def transcribe_file():
    """Transcribe audio from uploaded file"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Load and process audio
        audio_data, sample_rate = stt_server.audio_processor.load_audio_file(tmp_path)
        os.unlink(tmp_path)  # Clean up uploaded file
        
        if audio_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to load audio file'
            }), 400
        
        # Convert to target format
        processed_audio, target_sr = stt_server.audio_processor.convert_to_target_format(
            audio_data, sample_rate
        )
        
        if processed_audio is None:
            return jsonify({
                'success': False,
                'error': 'Failed to process audio'
            }), 400
        
        # Transcribe
        transcription, error = stt_server.transcribe_audio(processed_audio, target_sr)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        duration = len(processed_audio) / target_sr
        
        return jsonify({
            'success': True,
            'transcription': transcription,
            'audio_info': {
                'duration': duration,
                'sample_rate': target_sr,
                'channels': 1,
                'format': 'wav'
            },
            'processing_time': stt_server.stats['processing_times'][-1] if stt_server.stats['processing_times'] else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/transcribe_path', methods=['POST'])
def transcribe_path():
    """Transcribe audio from file path"""
    try:
        data = request.json
        if not data or 'file_path' not in data:
            return jsonify({
                'success': False,
                'error': 'No file path provided'
            }), 400
        
        file_path = data['file_path']
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': f'File not found: {file_path}'
            }), 400
        
        # Load and process audio
        audio_data, sample_rate = stt_server.audio_processor.load_audio_file(file_path)
        
        if audio_data is None:
            return jsonify({
                'success': False,
                'error': 'Failed to load audio file'
            }), 400
        
        # Convert to target format
        processed_audio, target_sr = stt_server.audio_processor.convert_to_target_format(
            audio_data, sample_rate
        )
        
        if processed_audio is None:
            return jsonify({
                'success': False,
                'error': 'Failed to process audio'
            }), 400
        
        # Transcribe
        transcription, error = stt_server.transcribe_audio(processed_audio, target_sr)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 500
        
        duration = len(processed_audio) / target_sr
        
        return jsonify({
            'success': True,
            'transcription': transcription,
            'file_path': file_path,
            'audio_info': {
                'duration': duration,
                'sample_rate': target_sr,
                'channels': 1,
                'format': 'wav'
            },
            'processing_time': stt_server.stats['processing_times'][-1] if stt_server.stats['processing_times'] else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/start_recording', methods=['POST'])
def start_recording():
    """Start microphone recording"""
    try:
        # Check if recording is already active
        if stt_server.microphone.is_recording:
            return jsonify({
                'success': False,
                'error': 'Recording already in progress',
                'current_state': 'recording'
            }), 400
        
        # Check if PyAudio is available
        try:
            import pyaudio
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'PyAudio not available - microphone recording not supported'
            }), 500
        
        # Try to start recording
        if stt_server.microphone.start_recording():
            recording_info = stt_server.microphone.get_recording_info()
            return jsonify({
                'success': True,
                'message': 'Recording started successfully',
                'recording_info': recording_info,
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start recording - check microphone availability',
                'troubleshooting': {
                    'check_microphone': 'Ensure microphone is connected and not being used by another application',
                    'check_permissions': 'Ensure microphone permissions are granted',
                    'try_different_browser': 'Some browsers have stricter audio policies'
                }
            }), 500
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Start recording error: {error_details}")
        
        return jsonify({
            'success': False,
            'error': f'Exception starting recording: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/stt/stop_recording', methods=['POST'])
def stop_recording():
    """Stop microphone recording and transcribe"""
    try:
        # Check if recording is active
        if not stt_server.microphone.is_recording:
            return jsonify({
                'success': False,
                'error': 'No active recording to stop',
                'current_state': 'not_recording'
            }), 400
        
        print("Attempting to stop recording...")
        
        # Stop recording and get audio data
        audio_data, sample_rate = stt_server.microphone.stop_recording()
        
        if audio_data is None or len(audio_data) == 0:
            return jsonify({
                'success': False,
                'error': 'No audio data recorded',
                'details': {
                    'possible_causes': [
                        'Recording duration too short',
                        'Microphone not working',
                        'Audio input level too low',
                        'Recording was interrupted'
                    ]
                }
            }), 400
        
        print(f"Audio data received: {len(audio_data)} samples at {sample_rate}Hz")
        
        # Check audio quality
        audio_rms = np.sqrt(np.mean(audio_data**2))
        if audio_rms < 0.001:  # Very quiet audio
            print(f"Warning: Very quiet audio detected (RMS: {audio_rms})")
        
        # Process audio to target format
        processed_audio, target_sr = stt_server.audio_processor.convert_to_target_format(
            audio_data, sample_rate
        )
        
        if processed_audio is None:
            return jsonify({
                'success': False,
                'error': 'Failed to process recorded audio',
                'details': 'Audio format conversion failed'
            }), 500
        
        print(f"Audio processed: {len(processed_audio)} samples at {target_sr}Hz")
        
        # Transcribe
        print("Starting transcription...")
        transcription, error = stt_server.transcribe_audio(processed_audio, target_sr)
        
        if error:
            return jsonify({
                'success': False,
                'error': f'Transcription failed: {error}',
                'audio_info': {
                    'duration': len(processed_audio) / target_sr,
                    'sample_rate': target_sr,
                    'audio_quality': 'recorded' if audio_rms > 0.001 else 'very_quiet'
                }
            }), 500
        
        if not transcription or transcription.strip() == "":
            return jsonify({
                'success': False,
                'error': 'Empty transcription result',
                'details': {
                    'possible_causes': [
                        'No speech detected in audio',
                        'Audio quality too poor',
                        'Language not recognized',
                        'Model processing error'
                    ]
                },
                'audio_info': {
                    'duration': len(processed_audio) / target_sr,
                    'sample_rate': target_sr,
                    'audio_rms': float(audio_rms)
                }
            }), 400
        
        duration = len(processed_audio) / target_sr
        processing_time = stt_server.stats['processing_times'][-1] if stt_server.stats['processing_times'] else 0
        
        print(f"Transcription completed: '{transcription}'")
        
        return jsonify({
            'success': True,
            'transcription': transcription,
            'audio_info': {
                'duration': duration,
                'sample_rate': target_sr,
                'channels': 1,
                'format': 'wav',
                'audio_rms': float(audio_rms),
                'quality_check': 'good' if audio_rms > 0.01 else 'low' if audio_rms > 0.001 else 'very_low'
            },
            'processing_time': processing_time,
            'timestamp': time.time()
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Stop recording error: {error_details}")
        
        # Try to cleanup recording state
        try:
            stt_server.microphone.is_recording = False
            stt_server.microphone._cleanup()
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': f'Exception stopping recording: {str(e)}',
            'error_type': type(e).__name__,
            'error_details': error_details if app.debug else None
        }), 500

@app.route('/stt/recording_status', methods=['GET'])
def recording_status():
    """Get current recording status"""
    try:
        status = {
            'is_recording': stt_server.microphone.is_recording,
            'recording_info': stt_server.microphone.get_recording_info(),
            'timestamp': time.time()
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/cancel_recording', methods=['POST'])
def cancel_recording():
    """Cancel current recording without transcription"""
    try:
        if not stt_server.microphone.is_recording:
            return jsonify({
                'success': False,
                'error': 'No active recording to cancel'
            }), 400
        
        # Stop recording without processing
        stt_server.microphone.is_recording = False
        stt_server.microphone._cleanup()
        
        # Clear the audio queue
        while not stt_server.microphone.audio_queue.empty():
            stt_server.microphone.audio_queue.get()
        
        return jsonify({
            'success': True,
            'message': 'Recording cancelled successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/calculate_accuracy', methods=['POST'])
def calculate_accuracy():
    """Calculate transcription accuracy"""
    try:
        data = request.json
        if not data or 'reference_text' not in data or 'transcribed_text' not in data:
            return jsonify({
                'success': False,
                'error': 'Reference text and transcribed text are required'
            }), 400
        
        reference_text = data['reference_text']
        transcribed_text = data['transcribed_text']
        
        accuracy_metrics = stt_server.calculate_accuracy(reference_text, transcribed_text)
        
        if accuracy_metrics is None:
            return jsonify({
                'success': False,
                'error': 'Failed to calculate accuracy'
            }), 500
        
        return jsonify({
            'success': True,
            'accuracy_metrics': accuracy_metrics
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    try:
        stats = stt_server.stats.copy()
        
        # Remove processing times list to reduce response size
        if 'processing_times' in stats:
            del stats['processing_times']
        
        # Calculate additional metrics
        uptime = time.time() - stats['start_time']
        success_rate = (stats['successful_transcriptions'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
        avg_accuracy = np.mean(stt_server.stats['accuracy_scores']) if stt_server.stats['accuracy_scores'] else 0
        
        stats.update({
            'uptime_seconds': uptime,
            'success_rate': success_rate,
            'average_accuracy': avg_accuracy
        })
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stt/reset_stats', methods=['POST'])
def reset_stats():
    """Reset server statistics"""
    try:
        stt_server.stats = {
            'total_requests': 0,
            'successful_transcriptions': 0,
            'failed_transcriptions': 0,
            'total_audio_duration': 0,
            'avg_processing_time': 0,
            'processing_times': [],
            'accuracy_scores': [],
            'start_time': time.time()
        }
        
        return jsonify({
            'success': True,
            'message': 'Statistics reset successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    print("="*60)
    print(f"🎤 STT Server Starting...")
    print(f"📁 Model Path: {MODEL_PATH}")
    print(f"🖥️  Device: {DEVICE}")
    print(f"🌐 Language: {LANGUAGE}")
    print(f"✅ Model Available: {stt_server.stt_model is not None}")
    
    # Check dependencies
    deps_available = {
        'librosa': True,
        'pyaudio': False,
        'transformers': CUSTOM_MODEL_AVAILABLE
    }
    
    try:
        import pyaudio
        deps_available['pyaudio'] = True
    except ImportError:
        print("WARNING: PyAudio not available - microphone recording disabled")
    
    print(f"Dependencies: {deps_available}")
    
    # Test microphone
    microphone_available = False
    if deps_available['pyaudio']:
        try:
            p = pyaudio.PyAudio()
            microphone_available = p.get_default_input_device_info() is not None
            p.terminate()
        except:
            pass
    
    print(f"Microphone Available: {microphone_available}")
    
    local_ip = get_local_ip()
    port = 5002
    
    print(f"\nServer Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\nSTT API Endpoints:")
    print(f"   Web Interface: GET /")
    print(f"   Health Check: GET /stt/health")
    print(f"   Transcribe File: POST /stt/transcribe_file")
    print(f"   Transcribe Path: POST /stt/transcribe_path")
    print(f"   Start Recording: POST /stt/start_recording")
    print(f"   Stop Recording: POST /stt/stop_recording")
    print(f"   Recording Status: GET /stt/recording_status")
    print(f"   Cancel Recording: POST /stt/cancel_recording")
    print(f"   Calculate Accuracy: POST /stt/calculate_accuracy")
    print(f"   Get Statistics: GET /stt/stats")
    print(f"   Reset Statistics: POST /stt/reset_stats")
    
    if not os.path.exists('stt_server_index.html'):
        print("WARNING: stt_server_index.html not found!")
    
    print("\n" + "="*60)
    print("STT Server ready... Press Ctrl+C to stop")
    print("="*60)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
            
        )
    except KeyboardInterrupt:
        print("\n\nShutting down STT server...")
        print("STT server stopped.")