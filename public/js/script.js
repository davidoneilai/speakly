document.addEventListener('DOMContentLoaded', () => {
  let mediaRecorder;
  let audioChunks = [];
  let stream;
  let selectedLevel = 'begginer'; // Valor padrão


  const startBtn = document.getElementById('start-btn');
  const stopBtn = document.getElementById('stop-btn');
  const status = document.getElementById('status-text');
  const waveImg = document.getElementById('wave');
  const chatContainer = document.getElementById('chat-container');
  const container = document.querySelector('.container');
  const levelButtons = document.querySelectorAll('.btn-level'); // Seleciona os botões de nível
  
  const WAVE_STATIC = 'img/audiowave.png';
  const WAVE_ANIMATED = 'img/audiowave.gif';

  waveImg.src = WAVE_STATIC;
  // Adiciona evento de clique nos botões de nível
  levelButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      selectedLevel = btn.getAttribute('data-level');
      // Destaca o botão selecionado
      levelButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateStatus(`Nível selecionado: ${btn.textContent}`, 'graduation-cap');
    });
  });
  // Função para atualizar o status
  function updateStatus(message, icon = 'info-circle') {
    status.innerHTML = `<i class="fas fa-${icon}"></i> ${message}`;
  }

  // Função para adicionar mensagem ao chat
  function addMessage(content, type = 'user', icon = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const iconClass = icon || (type === 'user' ? 'user' : 'robot');
    
    messageDiv.innerHTML = `
      <div class="message-header">
        <i class="fas fa-${iconClass}"></i>
        ${type === 'user' ? 'Você' : 'Assistente'}
      </div>
      <div class="message-content">${content}</div>
    `;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // Função para limpar mensagens antigas (manter apenas as últimas 10)
  function cleanOldMessages() {
    const messages = chatContainer.querySelectorAll('.message');
    if (messages.length > 10) {
      for (let i = 0; i < messages.length - 10; i++) {
        messages[i].remove();
      }
    }
  }

  startBtn.addEventListener('click', async () => {
    try {
      // Configurações otimizadas para captura de áudio
      const audioConstraints = {
        audio: {
          echoCancellation: true,    // Cancela eco
          noiseSuppression: true,    // Suprime ruído
          autoGainControl: true,     // Controle automático de ganho
          sampleRate: 44100,         // Taxa de amostragem alta
          channelCount: 1,           // Mono (suficiente para voz)
          volume: 1.0                // Volume máximo
        }
      };
      
      stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
      
      // Configurações otimizadas do MediaRecorder
      const options = {
        mimeType: 'audio/webm;codecs=opus', // Codec de alta qualidade
        audioBitsPerSecond: 128000  // 128kbps - boa qualidade
      };
      
      // Fallback para navegadores que não suportam o codec
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options.mimeType = 'audio/webm';
      }
      
      mediaRecorder = new MediaRecorder(stream, options);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

      mediaRecorder.onstart = () => {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        updateStatus('Escutando... Fale agora!', 'microphone');
        waveImg.src = WAVE_ANIMATED;
        container.classList.add('recording');
      };

      mediaRecorder.onstop = async () => {
        container.classList.remove('recording');
        container.classList.add('processing');
        waveImg.src = WAVE_STATIC;
        updateStatus('Processando áudio...', 'cog fa-spin');

        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const form = new FormData();
        form.append('file', audioBlob, 'recording.webm');
        form.append('user_level', selectedLevel); // Adiciona o nível ao FormData

        try {
          updateStatus('Transcrevendo...', 'language');
          
          const resp = await fetch('http://127.0.0.1:5000/api/stop_recording', {
            method: 'POST',
            body: form,
          });

          if (!resp.ok) {
            throw new Error(`Erro HTTP: ${resp.status}`);
          }

          const data = await resp.json();

          // Adicionar transcrição do usuário
          if (data.transcription) {
            addMessage(data.transcription, 'user');
            updateStatus('Gerando resposta...', 'brain');
          }

          // Adicionar resposta do assistente
          if (data.llm_response) {
            addMessage(data.llm_response, 'assistant');
            updateStatus('Convertendo em áudio...', 'volume-up');
          }

          // Reproduzir áudio da resposta
          if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            
            audio.addEventListener('play', () => {
              waveImg.src = WAVE_ANIMATED;
              updateStatus('Reproduzindo resposta...', 'volume-up');
            });
            
            audio.addEventListener('ended', () => {
              waveImg.src = WAVE_STATIC;
              updateStatus('Clique em "Iniciar Gravação" para continuar', 'microphone-alt');
              container.classList.remove('processing');
            });
            
            audio.addEventListener('pause', () => {
              waveImg.src = WAVE_STATIC;
              container.classList.remove('processing');
            });
            
            audio.addEventListener('error', () => {
              updateStatus('Erro ao reproduzir áudio', 'exclamation-triangle');
              container.classList.remove('processing');
            });
            
            audio.play();
          } else {
            updateStatus('Pronto para nova gravação', 'microphone-alt');
            container.classList.remove('processing');
          }

          cleanOldMessages();

        } catch (err) {
          console.error("Erro:", err);
          updateStatus('Erro ao processar áudio. Tente novamente.', 'exclamation-triangle');
          addMessage('Desculpe, ocorreu um erro ao processar sua solicitação.', 'assistant');
          container.classList.remove('processing');
        } finally {
          startBtn.disabled = false;
          if (stream) {
            stream.getTracks().forEach(track => track.stop());
          }
        }
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Erro ao acessar microfone:', err);
      updateStatus('Erro: Não foi possível acessar o microfone', 'exclamation-triangle');
    }
  });

  stopBtn.addEventListener('click', () => {
    stopBtn.disabled = true;
    updateStatus('Finalizando gravação...', 'stop');
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  });

  // Atalhos do teclado
  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !startBtn.disabled) {
      e.preventDefault();
      startBtn.click();
    } else if (e.code === 'Space' && !stopBtn.disabled) {
      e.preventDefault();
      stopBtn.click();
    }
  });

  // Mensagem inicial
  updateStatus('Clique em "Iniciar Gravação" ou pressione ESPAÇO para começar', 'microphone-alt');
});
