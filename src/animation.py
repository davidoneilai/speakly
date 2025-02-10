from PIL import Image, ImageTk, ImageSequence

def load_gif(gif_path):
    try:
        gif_image = Image.open(gif_path)
        gif_frames = [ImageTk.PhotoImage(frame) for frame in ImageSequence.Iterator(gif_image)]
        return gif_frames
    except Exception as e:
        print(f"Erro ao carregar o GIF: {e}")
        return None

def update_animation(frames, frame=0):
    if frames:
        return frames[frame], (frame + 1) % len(frames)