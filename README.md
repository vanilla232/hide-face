# hide-face

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Инструмент для защиты приватности на веб-камере. Маскирует лицо и отдаёт результат в виртуальную камеру, которую можно использовать в стриминговых приложениях или программах для видеосвязи.

Пока лицо в кадре — оно прячется одним из двух эффектов: чёрным прямоугольником
или breakcore-глитчем. Режимы переключаются жестом (закрытие глаз на три
секунды), что удобно для стримеров и не отвлекает от основного контента.

## Что умеет

- Находит лицо через MediaPipe FaceLandmarker (новый Tasks API).
- Два режима маскировки:
  - black — чёрный прямоугольник поверх лица для полной анонимности.
  - breakcore — пикселизация + сдвиги полос + RGB-разъезд + скан-линии + случайный текст (арт-эффект).
- Управление жестами для удобства во время стримов (без использования клавиатуры).
- Отдаёт видео в виртуальную камеру — выбираешь её в OBS или приложениях для видеосвязи.

## Что нужно

- Windows 10 / 11.
- Python 3.10 – 3.12. На 3.13 могут быть проблемы с mediapipe.
- Веб-камера.
- OBS Studio — один раз, чтобы поставить драйвер виртуальной камеры.

## Установка

Дважды кликни по run.bat. Всё остальное он сделает сам.

Если предпочитаешь руками:

```bash
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python hide-face.py
```

## Про OBS Virtual Camera

pyvirtualcam — это только мост. Чтобы виртуальная камера появилась в системе,
нужен драйвер. Проще всего:

1. Скачай и поставь OBS Studio: https://obsproject.com/
2. Запусти OBS один раз.
3. Нажми Start Virtual Camera, потом сразу Stop Virtual Camera.
4. Закрой OBS — он больше не нужен, драйвер уже в системе.

После этого в приложениях появится камера OBS Virtual Camera.

## Как пользоваться

1. Запусти hide-face.py (или run.bat).
2. Откроется окно с превью — там ты видишь себя уже с маской.
3. В приложении для стрима или видеосвязи выбери OBS Virtual Camera.
4. Чтобы выйти — нажми q в окне превью.

Переключение режимов: закрой оба глаза и держи их закрытыми 3 секунды.
Обычное моргание ничего не переключает.

## Настройки

Все параметры лежат в начале hide-face.py.

| Параметр | Что делает |
|---|---|
| CAM_INDEX | Индекс камеры. 0 — встроенная, 1 — внешняя. |
| MODES | Список режимов и порядок переключения. |
| EYES_CLOSED_SWITCH_SEC | Сколько держать глаза закрытыми для смены режима. |
| BREAKCORE_INTENSITY | Насколько жёстко глитчит breakcore. |
| SHOW_MODE_OSD | Показывать имя режима в углу кадра. |

## Если что-то не работает

ModuleNotFoundError: No module named 'cv2' — не активировано окружение.
Выполни .venv\Scripts\Activate и запусти снова.

PowerShell ругается на политику выполнения — один раз выполни:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

Виртуальная камера не появляется в приложении — перезапусти само приложение
после старта скрипта. И убедись, что OBS хотя бы раз активировал виртуальную камеру.

Маска дрожит или сползает — попробуй улучшить освещение.

Переключение режимов не срабатывает — уменьши EYES_CLOSED_SWITCH_SEC
до 2.0 или подними EAR_BLINK_THRESHOLD до 0.22.

---

# hide-face

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A privacy protection tool for your webcam. It masks your face and feeds the result into a virtual camera, which can be used in streaming apps or video conferencing software.

While your face is in the frame, it gets hidden by one of two effects:
a solid black rectangle or a breakcore glitch. Switch between them using a hands-free gesture (keeping both eyes closed for three seconds), which is convenient for streamers and doesn't distract from the content.

## Features

- Face detection via MediaPipe FaceLandmarker (new Tasks API).
- Two masking modes:
  - black — solid black rectangle over the face for full anonymity.
  - breakcore — pixelation + slice shifts + RGB split + scanlines + random text (artistic effect).
- Hands-free gesture control for convenience during streaming.
- Output goes to a virtual camera — select it in OBS or any video calling app.

## Requirements

- Windows 10 / 11.
- Python 3.10 – 3.12. 3.13 may have issues with mediapipe.
- A webcam.
- OBS Studio — once, just to install the virtual camera driver.

## Install

Double-click run.bat. It does everything else on its own.

Manual install:

```bash
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python hide-face.py
```

## OBS Virtual Camera

pyvirtualcam is only a bridge. You need the driver installed once:

1. Install OBS Studio: https://obsproject.com/
2. Launch it.
3. Click Start Virtual Camera, then Stop Virtual Camera.
4. Close OBS. The driver is now on your system.

After this, OBS Virtual Camera will appear in video apps.

## Usage

1. Run hide-face.py (or run.bat).
2. A preview window opens — you'll see yourself already masked.
3. In your streaming or video app, select OBS Virtual Camera.
4. Press q in the preview window to quit.

Switching modes: keep both eyes closed for 3 seconds. A regular blink
won't switch anything.

## Config

All settings are at the top of hide-face.py.

| Setting | What it does |
|---|---|
| CAM_INDEX | Camera index. 0 = built-in, 1 = external. |
| MODES | List of modes and their cycling order. |
| EYES_CLOSED_SWITCH_SEC | How long to keep eyes closed to switch. |
| BREAKCORE_INTENSITY | How hard the breakcore glitch hits. |
| SHOW_MODE_OSD | Show the mode name in the corner of the frame. |

## Troubleshooting

ModuleNotFoundError: No module named 'cv2' — virtual environment isn't
activated. Run .venv\Scripts\Activate and try again.

PowerShell complains about execution policy — run this once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

Virtual camera doesn't appear in the app — restart the app after starting
the script. Also make sure OBS was launched at least once to install the driver.

The mask jitters or slips off — try better lighting.

Mode switching doesn't trigger — lower EYES_CLOSED_SWITCH_SEC to 2.0
or raise EAR_BLINK_THRESHOLD to 0.22.