"""Loop credited stadium audio with smooth event swells and speech ducking."""
import subprocess, wave
from pathlib import Path
import numpy as np
from backend.commentary.config import MASTER_SAMPLE_RATE, COMMENTARY_DIR
class AmbientBedManager:
    def __init__(self, duration_seconds=310.7, sample_rate=MASTER_SAMPLE_RATE, source_ambient_path=None):
        self.duration_sec, self.sample_rate = duration_seconds, sample_rate
        self.total_samples = round(duration_seconds*sample_rate)
        self.source_path = Path(source_ambient_path) if source_ambient_path else COMMENTARY_DIR/"assets/stadium-cuauh89.mp3"
    def _create_clean_ambient_bed(self):
        if not self.source_path.exists():
            return np.zeros((2,self.total_samples),dtype=np.float32)
        result=subprocess.run(["ffmpeg","-v","error","-i",str(self.source_path),"-af","highpass=f=100,lowpass=f=4500",
            "-ar",str(self.sample_rate),"-ac","2","-f","f32le","pipe:1"],capture_output=True,check=True)
        source=np.frombuffer(result.stdout,dtype=np.float32).reshape(-1,2).T.copy()
        # Crossfade successive loops to avoid a click or an abrupt crowd change.
        fade=min(round(.6*self.sample_rate),source.shape[1]//4)
        stride=source.shape[1]-fade
        bed=np.zeros((2,self.total_samples),dtype=np.float32)
        for start in range(0,self.total_samples,stride):
            length=min(source.shape[1],self.total_samples-start)
            block=source[:,:length].copy()
            if start: block[:,:min(fade,length)]*=np.linspace(0,1,min(fade,length))
            if start+length<self.total_samples: block[:,-fade:]*=np.linspace(1,0,fade)
            bed[:,start:start+length]+=block
        rms=float(np.sqrt(np.mean(bed**2)))
        if rms: bed*=10**(-32/20)/rms
        return bed
    def generate_ducked_ambient_track(self, clips, output_path):
        bed=self._create_clean_ambient_bed()
        duck=np.ones(self.total_samples,dtype=np.float32)
        excitement=np.ones(self.total_samples,dtype=np.float32)
        for clip in clips:
            start=round(clip.pts_offset_seconds*self.sample_rate)
            end=min(self.total_samples,start+round(clip.actual_duration_ms/1000*self.sample_rate))
            if start>=self.total_samples: continue
            attack=max(0,start-round(.10*self.sample_rate))
            release=min(self.total_samples,end+round(.45*self.sample_rate))
            gain=10**(-7/20)
            if start>attack: duck[attack:start]=np.minimum(duck[attack:start],np.linspace(1,gain,start-attack))
            duck[start:end]=np.minimum(duck[start:end],gain)
            if release>end: duck[end:release]=np.minimum(duck[end:release],np.linspace(gain,1,release-end))
            if clip.slot_type in ("lead_in","shot_call","goal_reaction"):
                swell_end=min(self.total_samples,start+round((4 if clip.slot_type=="goal_reaction" else 2)*self.sample_rate))
                length=swell_end-start
                peak=2.5 if clip.slot_type=="goal_reaction" else 1.6
                envelope=1+(peak-1)*np.sin(np.linspace(0,np.pi,length))
                excitement[start:swell_end]=np.maximum(excitement[start:swell_end],envelope)
        bed*=duck*excitement
        fade=min(round(.8*self.sample_rate),self.total_samples//2)
        bed[:,:fade]*=np.linspace(0,1,fade)
        bed[:,-fade:]*=np.linspace(1,0,fade)
        output_path.parent.mkdir(parents=True,exist_ok=True)
        with wave.open(str(output_path),"wb") as f:
            f.setnchannels(2); f.setsampwidth(2); f.setframerate(self.sample_rate)
            f.writeframes((np.clip(bed,-.9,.9).T*32767).astype(np.int16).tobytes())
        return output_path
