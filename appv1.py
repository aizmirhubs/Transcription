import streamlit as st
import pyaudio
import wave
import threading
import time
from pydub import AudioSegment
import speech_recognition as sr
import os
import json
from datetime import datetime
import requests
import pyaudio
import wave



# Ses kaydı için ayarlar
FORMAT = pyaudio.paInt16  # 16-bit ses formatı
CHANNELS = 1            # Stereo ses
RATE = 44100              # Örnekleme hızı (44.1 kHz)
CHUNK = 1024              # Her bir okuma için örnek sayısı
RECORD_SECONDS = 5  
WAVE_OUTPUT_FILENAME_MIC = "mic_recording.wav"   
WAVE_OUTPUT_FILENAME = "ekran-sesi.wav"

# Kullanıcı bilgilerini saklamak için JSON dosyası
USER_CREDENTIALS_FILE = "user_credentials.json"

# Kullanıcı bilgilerini yükle veya oluştur
def load_user_credentials():
    if os.path.exists(USER_CREDENTIALS_FILE):
        with open(USER_CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

# Kullanıcı bilgilerini kaydet
def save_user_credentials(credentials):
    with open(USER_CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=4)

# Kullanıcı girişi kontrolü
def authenticate(username, password, title):  
    credentials = load_user_credentials()  
    if username in credentials:  
        if credentials[username]['password'] == password and credentials[username]['title'] == title:  
            return True  
    return False  

# Kullanıcı kaydı
def register_user(username, password, title  ):
    credentials = load_user_credentials()
    if username in credentials:
        return False  # Kullanıcı zaten var
    credentials[username] = {'password': password, 'title': title}
    save_user_credentials(credentials)
    return True

# Login arayüzü
def login_page():
    st.title("Giriş Yap veya Kayıt Ol")

    menu = ["Giriş Yap", "Kayıt Ol"]
    choice = st.selectbox("Menü", menu)

    if choice == "Giriş Yap":
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        title = st.text_input("Kullanıcı Unvanı")  # Kullanıcı unvanını al

        if st.button("Giriş Yap"):
            if authenticate(username, password,title):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Başarıyla giriş yapıldı!")
                st.rerun()
            else:
                st.error("Geçersiz kullanıcı adı, şifre veya unvan")

    elif choice == "Kayıt Ol":
        username = st.text_input("Yeni Kullanıcı Adı")
        password = st.text_input("Yeni Şifre", type="password")
        title = st.text_input("Kullanıcı Unvanı")  # Yeni unvan girişi

    if st.button("Kayıt Ol"):
        if register_user(username, password, title):
            st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
        else:
            st.error("Bu kullanıcı adı zaten alınmış.")

# Çıkış yap
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.success("Başarıyla çıkış yapıldı!")
    st.rerun()

# Konuşmalarda saat ve zaman damgası
def log_message(message):
    current_time = datetime.datetime.now()
    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)


p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("* cihaz (ekran sesi kaydediliyor)")

frames = []

for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("* kayit sonlandi")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()


# Ses kaydı sınıfı
class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames_mic = []  # Mikrofon sesi
        self.frames_system = []  # Sistem sesi
        self.audio = pyaudio.PyAudio()
        self.stream_mic = None
        self.stream_system = None

    def start_recording(self):
        # Eğer daha önce kayıt yapıldıysa, ses nesnesini yeniden başlat
        if not self.is_recording:
            self.is_recording = True
            self.frames_mic = []
            self.frames_system = []

            def record_mic():
                # Mikrofon sesini kaydet
                self.stream_mic = self.audio.open(format=FORMAT, channels=CHANNELS,
                                                  rate=RATE, input=True,
                                                  frames_per_buffer=CHUNK,
                                                  input_device_index=0)  # Mikrofon cihazı
                while self.is_recording:
                    data = self.stream_mic.read(CHUNK)
                    self.frames_mic.append(data)

            def record_system():
                # Sistem sesini kaydet
                self.stream_system = self.audio.open(format=FORMAT, channels=CHANNELS,
                                                     rate=RATE, input=True,
                                                     frames_per_buffer=CHUNK,
                                                     input_device_index=1)  # Sistem sesi cihazı
                while self.is_recording:
                    data = self.stream_system.read(CHUNK)
                    self.frames_system.append(data)

            # Mikrofon ve sistem sesi için ayrı thread'ler başlat
            self.recording_thread_mic = threading.Thread(target=record_mic)
            self.recording_thread_system = threading.Thread(target=record_system)
            self.recording_thread_mic.start()
            self.recording_thread_system.start()

    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'recording_thread_mic') and self.recording_thread_mic.is_alive():
            self.recording_thread_mic.join()
        if hasattr(self, 'recording_thread_system') and self.recording_thread_system.is_alive():
            self.recording_thread_system.join()
        if self.stream_mic:
            self.stream_mic.stop_stream()
            self.stream_mic.close()
        if self.stream_system:
            self.stream_system.stop_stream()
            self.stream_system.close()

    def save(self, filename_mic, filename_system):
        # Mikrofon sesini kaydet
        wf_mic = wave.open(filename_mic, 'wb')
        wf_mic.setnchannels(CHANNELS)
        wf_mic.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf_mic.setframerate(RATE)
        wf_mic.writeframes(b''.join(self.frames_mic))
        wf_mic.close()

        # Sistem sesini kaydet
        wf_system = wave.open(filename_system, 'wb')
        wf_system.setnchannels(CHANNELS)
        wf_system.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf_system.setframerate(RATE)
        wf_system.writeframes(b''.join(self.frames_system))
        wf_system.close()

    def reset(self):
        # Kayıt nesnesini sıfırla
        self.is_recording = False
        self.frames_mic = []
        self.frames_system = []
        if hasattr(self, 'stream_mic') and self.stream_mic:
            self.stream_mic.close()
        if hasattr(self, 'stream_system') and self.stream_system:
            self.stream_system.close()
        self.audio.terminate()
        self.audio = pyaudio.PyAudio()  # Yeni bir pyaudio nesnesi oluştur

def combine_audio_files(file_mic, file_system, output_file):
    """
    Mikrofon ve sistem sesini birleştirir.
    """
    sound_mic = AudioSegment.from_wav(file_mic)
    sound_system = AudioSegment.from_wav(file_system)
    
    combined = sound_mic.overlay(sound_system)  # Sesleri birleştir
    combined.export(output_file, format="wav")



# Ses dosyasını metne dönüştürürken tarih ve saat ekleyelim
def transcribe_audio(file_path):
    """
    Ses dosyasını metne dönüştürür ve her bir cümleye tarih/saat bilgisi ekler.
    """
    try:
        recognizer = sr.Recognizer()
        
        # Ses dosyasını yükle
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        
        # Google Web Speech API ile transkribe et
        text = recognizer.recognize_google(audio, language="tr-TR")
        
        # Şu anki tarih ve saat bilgisi
        current_time = datetime.now()
        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')  # Yıl-Ay-Gün Saat:Dakika:Saniye formatında
        
        # Konuşma metnini tarih/saat ile birleştirelim
        text_with_timestamp = f"[{timestamp}] {text}"
        
        return text_with_timestamp
    
    except sr.UnknownValueError:
        st.error("Ses anlaşılamadı")
        return None
    except sr.RequestError:
        st.error("API erişim hatası")
        return None
    except Exception as e:
        st.error(f"Transkripsiyon hatası: {str(e)}")
        return None

# Streamlit arayüzü
def main_app():
    # Üst kısımda "Hoş geldiniz" ve "Çıkış Yap" butonu
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"Hoş geldiniz, {st.session_state.username}!")
    with col2:
        if st.button("Çıkış Yap"):
            logout()

    # Session state ile durum yönetimi
    if 'audio_recorder' not in st.session_state:
        st.session_state.audio_recorder = AudioRecorder()
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'transcript' not in st.session_state:
        st.session_state.transcript = None

    # Kayıt kontrolleri
    if not st.session_state.recording:
        if st.button('Kaydı Başlat', key='start_recording'):
            # Önceki kayıt verilerini temizle
            st.session_state.audio_recorder.reset()
            st.session_state.audio_file = None
            st.session_state.transcript = None
            
            st.session_state.recording = True
            st.session_state.audio_recorder.start_recording()
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        if st.button('Kaydı Durdur', key='stop_recording'):
            st.session_state.audio_recorder.stop_recording()
            
            # Ses dosyalarını kaydet
            temp_mic_file = "mic_recording.wav"
            temp_system_file = "system_recording.wav"
            st.session_state.audio_recorder.save(temp_mic_file, temp_system_file)
            
            # Ses dosyalarını birleştir
            combined_file = "combined_recording.wav"
            combine_audio_files(temp_mic_file, temp_system_file, combined_file)
            st.session_state.audio_file = combined_file
            
            st.session_state.recording = False
            st.session_state.start_time = None
            st.rerun()

    # Kayıt durumunu ve süresini göster
    if st.session_state.recording:
        st.warning('Ses kaydı yapılıyor...')
        st.markdown("⏺️ Kayıt süresi: ")
        
        # Kayıt süresini güncelle
        duration_placeholder = st.empty()
        if st.session_state.start_time:
            duration = int(time.time() - st.session_state.start_time)
            duration_placeholder.markdown(f"{duration} saniye")

    # Kayıt durdurulduğunda sesi metne dönüştür
    # Streamlit arayüzünde konuşma metni ve tarih/saat bilgisi
    if st.session_state.audio_file and not st.session_state.recording:
        st.subheader("Ses Kaydı Tamamlandı")
        
        with st.spinner('Ses metne dönüştürülüyor...'):
            transcript = transcribe_audio(st.session_state.audio_file)
            
            if transcript:
                st.success("Metne dönüştürme tamamlandı!")
                st.session_state.transcript = transcript

                # Şu anki tarih ve saat bilgisi
                current_time = datetime.now()
                meeting_date = current_time.strftime('%d.%m.%Y')  # Gün.Ay.Yıl formatında
                meeting_time = current_time.strftime('%H:%M')  # Saat:Dakika formatında

                # Konuşma metninin sağ üst köşesinde tarih ve saat bilgisi
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; color: #000000; font-weight: bold;">
                    Toplantı Tarihi: {meeting_date} <br> Toplantı Saati: {meeting_time}
                </div>
                """, unsafe_allow_html=True)

                st.subheader("Transkripsiyon Sonucu")

                # Transkriptin altına ekleyelim
                st.text_area("Konuşma Metni", transcript, height=200)

                

                # JSON'a otomatik kaydet
                filename = f"toplanti_kayit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                data = {
                    "toplanti": {
                        "tarih": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "transcript": transcript
                    },
                    "genel_konusmalar": {
                        "transcript": transcript
                    }
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                st.success(f'Kayıt başarıyla kaydedildi: {filename}')
            else:
                st.error("Ses metne dönüştürülemedi.")
            
            # Geçici dosyaları temizle
            try:
                os.remove("mic_recording.wav")
                os.remove("system_recording.wav")
                os.remove(st.session_state.audio_file)
                st.session_state.audio_file = None
            except Exception as e:
                st.warning(f"Geçici dosya temizleme hatası: {str(e)}")

# Ana uygulama
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()