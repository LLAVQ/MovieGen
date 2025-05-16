# VidSynthAI

**VidSynthAI** is an AI-powered web app that transforms uploaded documents and images into stylish, narrated videos. It uses GPT for understanding content, FFmpeg for video generation, and several specialized tools for visual effects, watermarking, and audio.

---

## Features

- Upload PDFs, DOCX, Excel, images
- GPT-powered content summarization
- Video storyboard planning via YAML/JSON
- Real-time UI updates via WebSocket
- Stylized video rendering using FFmpeg and effects
- Voiceover with AI TTS (Step-Audio)
- Optional watermarking for unpaid users
- Captcha protection using CAP

---

## Technologies Used

### Frontend
- Vue 3 (Composition API)
- Tailwind CSS
- Anime.js / VueUse Motion
- WebSocket (real-time updates)

### Backend
- FastAPI
- Redis + Celery
- PostgreSQL (optional)
- Docker Compose

### Video & Media
- FFmpeg
- [ltxv.video](https://ltxv.video/)
- [WAN 2.1](https://github.com/facebookresearch/wav2lip) (neural animation)
- [Step-Audio](https://github.com/stepfun-ai/Step-Audio)
- [VideoSeal](https://github.com/facebookresearch/videoseal)
- [textbehindvideo](https://github.com/tansihmittal/textbehindvideo)

---

## Project Structure

```
/videos/
  /task-<uuid>/
    input/
    plan.yaml
    audio/
    frames/
    final/
```

---

## Workflow

1. User uploads files
2. Backend saves files and triggers background task
3. GPT analyzes contents and creates a YAML/JSON video plan
4. Python reads the plan, generates audio and renders scenes
5. FFmpeg stitches everything together
6. (Optional) Watermark applied if user is unpaid
7. Final video is sent to frontend

---

## Example YAML Plan

```yaml
frames:
  - number: 1
    type: "intro"
    text: "Welcome"
    voice: "tts:intro.wav"
    duration: 5
  - number: 2
    image: "image1.jpg"
    text: "Document summary..."
    voice: "tts:image1.wav"
    overlay: true
    duration: 6
  - number: 3
    type: "outro"
    text: "Thanks"
    voice: "tts:outro.wav"
    duration: 4
```

---

## WebSocket Events

- `task_started`
- `parsing`
- `gpt_ready`
- `tts_complete`
- `rendering_frame`
- `final_rendering`
- `complete`

---

## Run Locally

```bash
docker-compose up --build
```

---

## License

MIT (or your choice)

---

## Credits

Built with love using GPT-4, FFmpeg, and open-source magic.