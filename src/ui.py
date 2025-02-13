import tkinter as tk
from tkinter import Label
from src.recorder import start_recording, stop_recording
from src.transcriber import process_audio_with_llm
from src.animation import load_gif
from src.text_to_speech import text_to_speech, play_audio

def start_ui():
    global gif_label, gif_frames, animating, root, status_label

    root = tk.Tk()
    root.title("Gravador de Áudio para LLM")
    root.geometry("800x600")
    root.configure(bg="#2C3E50") 

    content_frame = tk.Frame(root, bg="#2C3E50")
    content_frame.pack(expand=True, fill="both", pady=20)

    gif_path = "img/ai_speaking.gif"
    gif_frames = load_gif(gif_path)
    gif_label = Label(content_frame, bg="#2C3E50")
    gif_label.pack(expand=True)

    control_frame = tk.Frame(root, bg="#34495E", padx=20, pady=20)
    control_frame.pack(side="bottom", fill="x")

    button_font = ("Helvetica", 12, "bold")

    start_button = tk.Button(
        control_frame,
        text="Iniciar Gravação",
        command=lambda: start_button_action(start_button, stop_button, status_label),
        width=20,
        font=button_font,
        bg="#27AE60",     
        fg="white",
        activebackground="#2ECC71",
        bd=0
    )
    start_button.grid(row=0, column=0, padx=10, pady=5)

    stop_button = tk.Button(
        control_frame,
        text="Parar Gravação",
        command=lambda: stop_button_action(start_button, stop_button, status_label),
        state=tk.DISABLED,
        width=20,
        font=button_font,
        bg="#C0392B",    
        fg="white",
        activebackground="#E74C3C",
        bd=0
    )
    stop_button.grid(row=0, column=1, padx=10, pady=5)

    status_label = tk.Label(
        control_frame,
        text="Clique em 'Iniciar Gravação' para começar.",
        font=("Helvetica", 12),
        bg="#34495E",
        fg="white",
        wraplength=760,  
        justify="left"  
    )
    status_label.grid(row=1, column=0, columnspan=2, pady=10, sticky="w")

    root.mainloop()

def animate_gif(frame=0):
    global animating, gif_label, gif_frames, root
    if animating and gif_frames:
        gif_label.configure(image=gif_frames[frame])
        root.after(100, lambda: animate_gif((frame + 1) % len(gif_frames)))

def start_button_action(start_button, stop_button, status_label):
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    status_label.config(text="Gravando...")
    start_recording()

def stop_button_action(start_button, stop_button, status_label):
    global animating
    stop_button.config(state=tk.DISABLED)
    filename = stop_recording()

    if filename:
        animating = True
        animate_gif()
        status_label.config(text="Processando áudio...")
        llm_response = process_audio_with_llm(filename)
        animating = False
        status_label.config(text=f"Resposta: {llm_response}")

        audio_file = text_to_speech(llm_response, lang='de')
        play_audio(audio_file)

    start_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    start_ui()