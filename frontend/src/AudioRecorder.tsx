import React, { useState, useRef } from "react";
import { Streamlit } from "streamlit-component-lib";

const AudioRecorder: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);

      mediaRecorder.current.ondataavailable = (e) => {
        audioChunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64data = reader.result?.toString().split(",")[1] || "";
          Streamlit.setComponentValue(base64data); // Kirim data ke Streamlit
        };
        reader.readAsDataURL(audioBlob);
        audioChunks.current = [];
      };

      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      Streamlit.setComponentValue("ERROR: Microphone access denied");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current) {
      mediaRecorder.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div style={{ padding: "1rem" }}>
      <button
        onClick={startRecording}
        disabled={isRecording}
        style={{
          backgroundColor: "#4CAF50",
          color: "white",
          padding: "12px 24px",
          border: "none",
          borderRadius: "25px",
          margin: "10px",
          cursor: "pointer",
          fontSize: "16px",
        }}
      >
        🎤 Mulai Rekam
      </button>
      <button
        onClick={stopRecording}
        disabled={!isRecording}
        style={{
          backgroundColor: "#f44336",
          color: "white",
          padding: "12px 24px",
          border: "none",
          borderRadius: "25px",
          margin: "10px",
          cursor: "pointer",
          fontSize: "16px",
        }}
      >
        ⏹️ Hentikan Rekam
      </button>
    </div>
  );
};

export default AudioRecorder;
