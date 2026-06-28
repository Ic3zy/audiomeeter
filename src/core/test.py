import numpy as np
import soundcard as sc

def play_zero_db_tone(duration=5.0, frequency=440.0):
    samplerate = 44100
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    amplitude = 1.0 
    
    tone = amplitude * np.sin(2 * np.pi * frequency * t)
    
    stereo_tone = np.vstack((tone, tone)).T
    
    speaker = sc.default_speaker()
    print(f" cihaz: '{speaker.name}' üzerinden 0 dBFS ses")
    
    speaker.play(stereo_tone, samplerate=samplerate)

if __name__ == "__main__":
    play_zero_db_tone(duration=40.0)