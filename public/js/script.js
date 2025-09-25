document.addEventListener('DOMContentLoaded', () => {
  let mediaRecorder;
  let audioChunks = [];
  let stream;
  let selectedLevel = 'begginer'; // Valor padrão
  let selectedTheme = 'conversacao-geral'; // Valor padrão
  let isAudioPlaying = false; // Nova variável para controlar áudio
  let currentAudio = null; // Referência ao áudio atual
  let firstResponseReceived = false; // Flag para controlar exibição dos botões flutuantes

  // Elementos da navbar
  const difficultyBtn = document.getElementById('difficulty-btn');
  const difficultyDropdown = document.getElementById('difficulty-dropdown');
  const difficultyText = document.getElementById('difficulty-text');
  const themeButtons = document.querySelectorAll('.theme-btn');
  const customThemeInput = document.getElementById('custom-theme-input');
  const customThemeBtn = document.getElementById('custom-theme-btn');

  // Elementos principais
  const startBtn = document.getElementById('start-btn');
  const stopBtn = document.getElementById('stop-btn');
  const status = document.getElementById('status-text');
  const waveImg = document.getElementById('wave');
  const chatContainer = document.getElementById('chat-container');
  const container = document.querySelector('.container');
  
  // Botões flutuantes
  const floatingStartBtn = document.getElementById('floating-start-btn');
  const floatingStopBtn = document.getElementById('floating-stop-btn');
  const floatingControls = document.getElementById('floating-controls');
  
  console.log('Floating buttons found:', floatingStartBtn, floatingStopBtn); // Debug
  
  const WAVE_STATIC = 'img/audiowave.png';
  const WAVE_ANIMATED = 'img/audiowave.gif';

  waveImg.src = WAVE_STATIC;

  // Funcionalidade do dropdown de dificuldade
  difficultyBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const dropdown = difficultyBtn.parentElement;
    dropdown.classList.toggle('active');
  });

  // Fechar dropdown ao clicar fora
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
      document.querySelectorAll('.dropdown').forEach(dropdown => {
        dropdown.classList.remove('active');
      });
    }
  });

  // Seleção de dificuldade
  difficultyDropdown.addEventListener('click', (e) => {
    if (e.target.classList.contains('dropdown-option')) {
      e.preventDefault();
      
      // Remove active de todas as opções
      difficultyDropdown.querySelectorAll('.dropdown-option').forEach(option => {
        option.classList.remove('active');
      });
      
      // Adiciona active na opção clicada
      e.target.classList.add('active');
      
      // Atualiza valores
      selectedLevel = e.target.getAttribute('data-value');
      difficultyText.textContent = e.target.textContent;
      
      // Fecha dropdown
      difficultyBtn.parentElement.classList.remove('active');
      
      updateStatus(`Difficulty selected: ${e.target.textContent}`, 'graduation-cap');
    }
  });

  // Funcionalidade dos botões de tema
  themeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      // Remove active de todos os botões
      themeButtons.forEach(b => b.classList.remove('active'));
      
      // Adiciona active no botão clicado
      btn.classList.add('active');
      
      // Atualiza tema selecionado
      selectedTheme = btn.getAttribute('data-theme');
      
      // Limpa input customizado
      customThemeInput.value = '';
      
      updateStatus(`Theme selected: ${btn.textContent}`, 'tags');
    });
  });

  // Funcionalidade do tema customizado
  if (customThemeBtn && customThemeInput) {
    customThemeBtn.addEventListener('click', () => {
    const customTheme = customThemeInput.value.trim();
    if (customTheme) {
      // Remove active de todos os botões de tema fixos
      themeButtons.forEach(b => b.classList.remove('active'));
      
      // Define tema customizado
      selectedTheme = customTheme;
      
      updateStatus(`Custom theme: ${customTheme}`, 'lightbulb');
      
      // Limpa o input
      customThemeInput.value = '';
    } else {
      updateStatus('Enter a custom theme first', 'exclamation-triangle');
    }
    });

    // Permitir Enter no input de tema customizado
    customThemeInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        customThemeBtn.click();
      }
    });
  }

  // Função para atualizar o status
  function updateStatus(message, icon = 'info-circle') {
    status.innerHTML = `<i class="fas fa-${icon}"></i> ${message}`;
  }

  // Função para adicionar mensagem ao chat
  function addMessage(content, type = 'user', icon = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const iconClass = icon || (type === 'user' ? 'user' : 'robot');
    
    // Debug: verificar se está criando botão para assistente
    console.log('Adicionando mensagem:', type, 'Vai ter botão?', type === 'assistant');
    
    messageDiv.innerHTML = `
      <div class="message-header">
        <i class="fas fa-${iconClass}"></i>
        ${type === 'user' ? 'You' : 'Assistant'}
      </div>
      <div class="message-content">${content}</div>
      ${type === 'assistant' ? '<div class="message-actions"><button class="translate-btn" onclick="translateMessage(this)"><i class="fas fa-language"></i> Translate</button></div>' : ''}
      <div class="translation-container" style="display: none;"></div>
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
    // Verificar se há áudio tocando
    if (isAudioPlaying) {
      updateStatus('Wait for the assistant to finish speaking...', 'exclamation-triangle');
      return;
    }
    
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
        updateStatus('Listening... Speak now!', 'microphone');
        waveImg.src = WAVE_ANIMATED;
        container.classList.add('recording');
      };

      mediaRecorder.onstop = async () => {
        container.classList.remove('recording');
        container.classList.add('processing');
        waveImg.src = WAVE_STATIC;
        updateStatus('Processing audio...', 'cog fa-spin');

        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const form = new FormData();
        form.append('file', audioBlob, 'recording.webm');
        form.append('user_level', selectedLevel); // Adiciona o nível ao FormData
        form.append('theme', selectedTheme); // Adiciona o tema ao FormData

        try {
          updateStatus('Transcribing...', 'language');
          
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
            updateStatus('Generating response...', 'brain');
          }

          // Adicionar resposta do assistente
          if (data.llm_response) {
            addMessage(data.llm_response, 'assistant');
            updateStatus('Converting to audio...', 'volume-up');
            
            // Mostrar botões flutuantes após primeira resposta
            if (!firstResponseReceived) {
              firstResponseReceived = true;
              showFloatingControls();
            }
          }

          // Reproduzir áudio da resposta
          if (data.audio_url) {
            // Parar áudio anterior se existir
            if (currentAudio) {
              currentAudio.pause();
              currentAudio = null;
            }
            
            const audio = new Audio(data.audio_url);
            currentAudio = audio;
            
            audio.addEventListener('loadstart', () => {
              isAudioPlaying = true;
              startBtn.disabled = true; // Desabilitar botão de gravação
            });
            
            audio.addEventListener('play', () => {
              isAudioPlaying = true;
              startBtn.disabled = true;
              waveImg.src = WAVE_ANIMATED;
              updateStatus('Playing response... (Recording disabled)', 'volume-up');
            });
            
            audio.addEventListener('ended', () => {
              isAudioPlaying = false;
              startBtn.disabled = false; // Reabilitar botão de gravação
              currentAudio = null;
              waveImg.src = WAVE_STATIC;
              updateStatus('Click "Start Recording" to continue', 'microphone-alt');
              container.classList.remove('processing');
            });
            
            audio.addEventListener('pause', () => {
              isAudioPlaying = false;
              startBtn.disabled = false;
              currentAudio = null;
              waveImg.src = WAVE_STATIC;
              container.classList.remove('processing');
            });
            
            audio.addEventListener('error', () => {
              isAudioPlaying = false;
              startBtn.disabled = false;
              currentAudio = null;
              updateStatus('Error playing audio', 'exclamation-triangle');
              container.classList.remove('processing');
            });
            
            audio.play();
          } else {
            updateStatus('Ready for new recording', 'microphone-alt');
            container.classList.remove('processing');
          }

          cleanOldMessages();

        } catch (err) {
          console.error("Erro:", err);
          updateStatus('Error processing audio. Please try again.', 'exclamation-triangle');
          addMessage('Sorry, an error occurred while processing your request.', 'assistant');
          container.classList.remove('processing');
        } finally {
          // Só reabilitar o botão se não houver áudio tocando
          if (!isAudioPlaying) {
            startBtn.disabled = false;
          }
          if (stream) {
            stream.getTracks().forEach(track => track.stop());
          }
        }
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Error accessing microphone:', err);
      updateStatus('Error: Could not access microphone', 'exclamation-triangle');
    }
  });

  stopBtn.addEventListener('click', () => {
    stopBtn.disabled = true;
    updateStatus('Finishing recording...', 'stop');
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
  });

  // Atalhos do teclado
  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !startBtn.disabled && !isAudioPlaying) {
      e.preventDefault();
      startBtn.click();
    } else if (e.code === 'Space' && !stopBtn.disabled) {
      e.preventDefault();
      stopBtn.click();
    } else if (e.code === 'Space' && isAudioPlaying) {
      e.preventDefault();
      updateStatus('Wait for the assistant to finish speaking...', 'exclamation-triangle');
    }
  });

  // Função para mostrar os botões flutuantes
  function showFloatingControls() {
    if (floatingControls) {
      floatingControls.style.display = 'flex';
      syncFloatingButtons();
    }
  }

  // Função para sincronizar os botões flutuantes com os principais
  function syncFloatingButtons() {
    // Só sincronizar se os botões flutuantes já foram mostrados
    if (!firstResponseReceived || !floatingControls || floatingControls.style.display === 'none') {
      return;
    }
    
    if (startBtn.disabled || isAudioPlaying) {
      floatingStartBtn.style.display = 'none';
      floatingStopBtn.style.display = 'flex';
    } else {
      floatingStartBtn.style.display = 'flex';
      floatingStopBtn.style.display = 'none';
    }
  }
  
  // Event listeners para os botões flutuantes
  if (floatingStartBtn && floatingStopBtn) {
    floatingStartBtn.addEventListener('click', () => {
      console.log('Floating start button clicked!'); // Debug
      startBtn.click(); // Reutiliza a lógica do botão principal
    });
    
    floatingStopBtn.addEventListener('click', () => {
      console.log('Floating stop button clicked!'); // Debug
      stopBtn.click(); // Reutiliza a lógica do botão principal
    });
    
    // Observar mudanças nos botões principais para sincronizar os flutuantes
    const observer = new MutationObserver(() => {
      syncFloatingButtons();
    });
    
    // Observar mudanças nos atributos disabled dos botões principais
    observer.observe(startBtn, { attributes: true, attributeFilter: ['disabled'] });
    observer.observe(stopBtn, { attributes: true, attributeFilter: ['disabled'] });
    
    // Sincronização inicial
    syncFloatingButtons();
    console.log('Floating buttons initialized!'); // Debug
  } else {
    console.error('Floating buttons not found!'); // Debug
  }

  // Mensagem inicial
  updateStatus('Click "Start Recording" or press SPACE to begin', 'microphone-alt');
});

// Função global para traduzir mensagem
async function translateMessage(button) {
  const messageDiv = button.closest('.message');
  const messageContent = messageDiv.querySelector('.message-content').textContent;
  const translationContainer = messageDiv.querySelector('.translation-container');
  
  // Se já está traduzido, esconder tradução
  if (translationContainer.style.display !== 'none') {
    translationContainer.style.display = 'none';
    button.innerHTML = '<i class="fas fa-language"></i> Translate';
    return;
  }
  
  // Mostrar loading
  button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
  button.disabled = true;
  
  try {
    const response = await fetch('http://127.0.0.1:5000/api/translate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: messageContent })
    });
    
    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Mostrar tradução
    translationContainer.innerHTML = `
      <div class="translation-text">
        <i class="fas fa-globe"></i>
        <span>${data.translated_text}</span>
      </div>
    `;
    translationContainer.style.display = 'block';
    
    // Atualizar botão
    button.innerHTML = '<i class="fas fa-eye-slash"></i> Hide';
    
  } catch (error) {
    console.error('Error translating:', error);
    translationContainer.innerHTML = `
      <div class="translation-error">
        <i class="fas fa-exclamation-triangle"></i>
        Error translating text
      </div>
    `;
    translationContainer.style.display = 'block';
    button.innerHTML = '<i class="fas fa-language"></i> Translate';
  } finally {
    button.disabled = false;
  }
}
