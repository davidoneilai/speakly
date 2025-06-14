document.addEventListener('DOMContentLoaded', () => {
  let mediaRecorder;
  let audioChunks = [];
  let stream;

  const startBtn = document.getElementById('start-btn');
  const stopBtn  = document.getElementById('stop-btn');
  const status   = document.getElementById('status-text');
  const waveImg = document.getElementById('wave');
  const WAVE_STATIC = 'img/audiowave.png';
  const WAVE_ANIMATED = 'img/audiowave.gif';

  waveImg.src = WAVE_STATIC;  // Inicialmente, onda parada

  startBtn.addEventListener('click', async () => {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

    mediaRecorder.onstart = () => {
      startBtn.disabled = true;
      stopBtn.disabled = false;
      status.textContent = 'Gravando...';
      waveImg.src = WAVE_ANIMATED; // Onda animada ao gravar
    };

    mediaRecorder.onstop = async () => {
      waveImg.src = WAVE_STATIC; // Onda parada ao processar
      status.textContent = 'Processando áudio...';
      console.log('Entrou no onstop');

      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });  // use 'webm' pois é o formato real
      console.log("Blob:", audioBlob);

      const form = new FormData();
      form.append('file', audioBlob, 'recording.webm');

      try {
        const resp = await fetch('http://127.0.0.1:5000/api/stop_recording', {
          method: 'POST',
          body: form,
        });
        console.log("Resposta Fetch:", resp);

        const data = await resp.json();
        console.log("JSON recebido:", data);
        
        if (data.llm_response) {
          status.textContent = `Resposta: ${data.llm_response}`;
        }

        if (data.audio_url) {
          const audio = new Audio(data.audio_url);
          audio.addEventListener('play', () => {
            waveImg.src = WAVE_ANIMATED; // Onda animada ao reproduzir
          });
          audio.addEventListener('ended', () => {
            waveImg.src = WAVE_STATIC; // Onda parada ao terminar reprodução
          });
          audio.addEventListener('pause', () => {
            waveImg.src = WAVE_STATIC;
          });
          audio.play();
        }

      } catch (err) {
        console.error("Erro:", err);
        status.textContent = 'Erro ao processar áudio.';
      } finally {
        startBtn.disabled = false;
        stream.getTracks().forEach(track => track.stop());
      }
    };

    mediaRecorder.start();
  });

  stopBtn.addEventListener('click', () => {
    console.log('Cliquei em PARAR');
    stopBtn.disabled = true;

    mediaRecorder.stop();
  });
});
