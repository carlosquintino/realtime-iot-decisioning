"""
farm_viz.py  —  FARM SIDE (visualização)
=========================================
Renderiza a simulação da fazenda como uma "caixa" gráfica (pygame) mostrando,
a cada dia: a lavoura, o estágio da cultura, a umidade do solo, o clima e —
em destaque — a AÇÃO que a IA decidiu naquele dia:

    • REGAR            → gotas de água caindo + faixa "IRRIGAÇÃO: X mm"
    • REGAR + N        → gotas + pellets de adubo + faixa "NITROGÊNIO: X kg"
    • (sem ação)       → nota discreta "Sem ação"

Sempre exibe a DATA e o número de DIAS passados na simulação.

Modo de saída
-------------
Roda headless (sem janela), desenhando numa Surface off-screen e montando um
vídeo MP4 (animação completa) e um GIF leve (resumo, 1 quadro/dia). Se houver
um display (DISPLAY setado), também abre uma janela ao vivo.

Uso típico (via run_farm.py --viz). Programaticamente:

    viz = FarmVisualizer(out_path="sim_farm.mp4",
                         crop_name="Batata", location="Suzano-SP")
    viz.render_day(day_index=0, sim_date=date(2006,1,1),
                   metrics={"DVS":0.1,"LAI":0.2,"SM":0.3,...},
                   action={"irrigation":0,"N":0})
    ...
    viz.close()   # finaliza o MP4/GIF
"""

import os
import io
import math
import random
import threading
import http.server
import socketserver
from datetime import date

# Sem display? roda em modo dummy (não tenta abrir janela do SO).
_HAS_DISPLAY = bool(os.environ.get("DISPLAY"))
if not _HAS_DISPLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Esconde o banner "Hello from pygame" no import.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np
import pygame


# ── paleta ───────────────────────────────────────────────────────────────────
SKY_TOP      = (120, 186, 235)
SKY_BOTTOM   = (205, 232, 247)
SUN          = (255, 214, 70)
SUN_DIM      = (210, 210, 200)
CLOUD        = (235, 238, 242)
RAIN         = (90, 150, 220)
WATER        = (40, 130, 220)
SOIL_DRY     = (197, 162, 110)   # solo seco (claro)
SOIL_WET     = (96, 64, 36)      # solo úmido (escuro)
LEAF         = (46, 160, 56)
LEAF_DRY     = (170, 150, 50)    # folha sob estresse hídrico
LEAF_PALE    = (150, 180, 90)    # folha sob carência de N
STEM         = (70, 120, 45)
PELLET       = (120, 80, 40)
WHITE        = (250, 250, 250)
BLACK        = (20, 20, 20)
PANEL_BG     = (15, 30, 45)
BANNER_WATER = (21, 101, 192)
BANNER_N     = (46, 125, 50)
ACCENT       = (255, 235, 130)


def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _g(metrics, key, default=0.0):
    """Lê uma métrica de forma tolerante (valor pode ser None)."""
    v = metrics.get(key, default)
    return default if v is None else float(v)


class _LiveServer:
    """Servidor HTTP que transmite os quadros ao vivo (MJPEG) para o navegador.

    `/`            → página HTML com <img> apontando para o stream
    `/stream.mjpg` → multipart/x-mixed-replace, empurra o último quadro ~fps
    """

    def __init__(self, port, title, fps):
        self.port = port
        self.title = title
        self.fps = max(1, fps)
        self._jpeg = None
        self._cond = threading.Condition()
        self._httpd = None
        self._thread = None

    def update(self, jpeg_bytes):
        with self._cond:
            self._jpeg = jpeg_bytes
            self._cond.notify_all()

    def start(self):
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # silencia o log de acesso
                pass

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    body = (
                        "<!doctype html><html><head><meta charset='utf-8'>"
                        f"<title>{server.title}</title>"
                        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                        "<style>html,body{margin:0;height:100%;background:#0b1220;"
                        "font-family:sans-serif}.wrap{display:flex;flex-direction:column;"
                        "align-items:center;justify-content:center;height:100%}"
                        "h1{color:#cfe3ff;font-size:15px;margin:8px;opacity:.7}"
                        "img{max-width:100%;max-height:92vh;box-shadow:0 0 30px #000}</style>"
                        "</head><body><div class='wrap'>"
                        f"<h1>{server.title} — ao vivo</h1>"
                        "<img src='/stream.mjpg' alt='aguardando simulação...'>"
                        "</div></body></html>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif self.path == "/stream.mjpg":
                    self.send_response(200)
                    self.send_header("Cache-Control", "no-cache, private")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Connection", "close")
                    self.send_header(
                        "Content-Type",
                        "multipart/x-mixed-replace; boundary=FRAME",
                    )
                    self.end_headers()
                    try:
                        while True:
                            with server._cond:
                                server._cond.wait(timeout=1.0 / server.fps)
                                frame = server._jpeg
                            if frame is None:
                                continue
                            self.wfile.write(b"--FRAME\r\n")
                            self.wfile.write(b"Content-Type: image/jpeg\r\n")
                            self.wfile.write(
                                f"Content-Length: {len(frame)}\r\n\r\n".encode()
                            )
                            self.wfile.write(frame)
                            self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass
                else:
                    self.send_error(404)

        self._httpd = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), Handler)
        self._httpd.daemon_threads = True
        self._httpd.allow_reuse_address = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:  # noqa: BLE001
                pass


class FarmVisualizer:
    def __init__(self,
                 out_path="sim_farm.mp4",
                 crop_name="Cultura",
                 location="",
                 total_days=None,
                 width=960,
                 height=600,
                 fps=12,
                 frames_per_day=16,
                 n_plants=6,
                 also_gif=True,
                 live=False,
                 live_port=8090):
        self.W, self.H = width, height
        self.crop_name = crop_name
        self.location = location
        self.total_days = total_days
        self.fps = fps
        self.frames_per_day = max(2, frames_per_day)
        self.n_plants = n_plants
        self.out_path = out_path
        self.also_gif = also_gif
        self.live = live

        self.headless = not _HAS_DISPLAY
        self.ground_y = int(self.H * 0.60)   # linha do horizonte/solo

        pygame.init()
        pygame.font.init()
        if self.headless:
            self.surface = pygame.Surface((self.W, self.H))
            self.window = None
        else:
            self.window = pygame.display.set_mode((self.W, self.H))
            pygame.display.set_caption("Fazenda — Simulação IoT/IA")
            self.surface = pygame.Surface((self.W, self.H))
        self.clock = pygame.time.Clock()

        self.f_title = pygame.font.SysFont("dejavusans", 24, bold=True)
        self.f_big   = pygame.font.SysFont("dejavusans", 30, bold=True)
        self.f_med   = pygame.font.SysFont("dejavusans", 20, bold=True)
        self.f_small = pygame.font.SysFont("dejavusans", 16)

        # writers (lazy / só no fim para o gif)
        self._writer = None
        self._gif_frames = []
        try:
            import imageio
            self._imageio = imageio
            self._writer = imageio.get_writer(
                out_path, fps=fps, macro_block_size=None,
                codec="libx264", quality=8,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[viz] aviso: não foi possível abrir o MP4 ({e}); só GIF.")
            self._imageio = None

        # posições fixas das plantas (x) e jitter de balanço por planta
        margin = int(self.W * 0.10)
        span = self.W - 2 * margin
        self._plant_x = [int(margin + span * (i + 0.5) / n_plants)
                         for i in range(n_plants)]
        self._sway_seed = [random.uniform(0, math.tau) for _ in range(n_plants)]

        # servidor de transmissão ao vivo p/ o navegador (MJPEG)
        self._live = None
        self._pil = None
        if live:
            try:
                from PIL import Image
                self._pil = Image
                title = crop_name + (f" — {location}" if location else "")
                self._live = _LiveServer(live_port, title, fps)
                self._live.start()
                print(f"[viz] transmissão ao vivo em http://0.0.0.0:{live_port}/ "
                      f"(MJPEG; abra no navegador)")
            except Exception as e:  # noqa: BLE001
                print(f"[viz] aviso: não foi possível iniciar a transmissão ao vivo: {e}")
                self._live = None

    # ── API pública ───────────────────────────────────────────────────────────
    def render_day(self, day_index, sim_date, metrics, action):
        """Desenha um dia inteiro (vários quadros para animar a ação)."""
        irrig = float(action.get("irrigation", 0) or 0)
        nkg = float(action.get("N", 0) or 0)

        for f in range(self.frames_per_day):
            prog = f / (self.frames_per_day - 1)   # 0..1 dentro do dia
            self._draw_scene(day_index, sim_date, metrics, irrig, nkg, prog, f)
            self._emit_frame(gif=(f == self.frames_per_day - 1))

    def close(self):
        if self._writer is not None:
            try:
                self._writer.close()
                print(f"[viz] vídeo salvo: {self.out_path}")
            except Exception as e:  # noqa: BLE001
                print(f"[viz] erro ao fechar MP4: {e}")
        if self.also_gif and self._gif_frames and self._imageio is not None:
            gif_path = os.path.splitext(self.out_path)[0] + ".gif"
            try:
                self._imageio.mimsave(gif_path, self._gif_frames,
                                      duration=1.0 / max(1, self.fps // 2), loop=0)
                print(f"[viz] gif salvo: {gif_path}")
            except Exception as e:  # noqa: BLE001
                print(f"[viz] erro ao salvar GIF: {e}")
        if self._live is not None:
            self._live.stop()
        pygame.quit()

    # ── desenho ────────────────────────────────────────────────────────────────
    def _draw_scene(self, day_index, sim_date, metrics, irrig, nkg, prog, frame):
        s = self.surface
        raining = _g(metrics, "RAIN") > 0.5

        self._draw_sky(s, raining)
        self._draw_sun_or_clouds(s, raining, prog)
        if raining:
            self._draw_rain(s, prog)
        self._draw_soil(s, _g(metrics, "SM"))
        self._draw_plants(s, metrics, prog)

        if irrig > 0:
            self._draw_water_action(s, prog)
        if nkg > 0:
            self._draw_nitrogen_action(s, prog)

        self._draw_action_border(s, irrig, nkg, frame)
        self._draw_hud(s, day_index, sim_date, metrics)
        self._draw_action_banner(s, irrig, nkg)

    def _draw_sky(self, s, raining):
        top = (110, 120, 140) if raining else SKY_TOP
        bot = (170, 178, 190) if raining else SKY_BOTTOM
        for y in range(0, self.ground_y):
            t = y / self.ground_y
            pygame.draw.line(s, _lerp(top, bot, t), (0, y), (self.W, y))

    def _draw_sun_or_clouds(self, s, raining, prog):
        cx, cy = self.W - 90, 80
        if raining:
            # nuvens cinza
            for off in (-30, 0, 28):
                pygame.draw.circle(s, (120, 124, 130), (cx + off, cy), 28)
            pygame.draw.circle(s, (140, 144, 150), (cx, cy - 12), 30)
        else:
            # raios pulsando levemente
            r = 34 + int(3 * math.sin(prog * math.tau))
            for i in range(12):
                ang = i * math.tau / 12 + prog * 0.5
                x1 = cx + int(math.cos(ang) * (r + 8))
                y1 = cy + int(math.sin(ang) * (r + 8))
                x2 = cx + int(math.cos(ang) * (r + 22))
                y2 = cy + int(math.sin(ang) * (r + 22))
                pygame.draw.line(s, SUN, (x1, y1), (x2, y2), 3)
            pygame.draw.circle(s, SUN, (cx, cy), r)

    def _draw_rain(self, s, prog):
        random.seed(7)
        for _ in range(120):
            x = random.randint(0, self.W)
            y0 = random.randint(0, self.ground_y)
            y = int((y0 + prog * 80) % self.ground_y)
            pygame.draw.line(s, RAIN, (x, y), (x - 3, y + 12), 2)

    def _draw_soil(self, s, sm):
        # SM ~ 0.10 (seco) .. 0.45 (úmido)
        t = (sm - 0.10) / (0.40 - 0.10)
        color = _lerp(SOIL_DRY, SOIL_WET, t)
        pygame.draw.rect(s, color, (0, self.ground_y, self.W, self.H - self.ground_y))
        # sulcos do canteiro
        dark = _lerp(color, BLACK, 0.18)
        for i in range(1, 7):
            y = self.ground_y + int((self.H - self.ground_y) * i / 7)
            pygame.draw.line(s, dark, (0, y), (self.W, y), 1)

    def _draw_plants(self, s, metrics, prog):
        dvs = _g(metrics, "DVS")
        lai = _g(metrics, "LAI")
        rftra = _g(metrics, "RFTRA", 1.0)   # 1 = sem estresse hídrico
        nni = _g(metrics, "NNI", 1.0)       # 1 = N ok
        for i, x in enumerate(self._plant_x):
            sway = math.sin(prog * math.tau + self._sway_seed[i]) * 3
            self._draw_plant(s, x + sway, self.ground_y + 6, dvs, lai, rftra, nni)

    def _draw_plant(self, s, x, base_y, dvs, lai, rftra, nni):
        x = int(x)
        # altura cresce com LAI (limitado) e cai na senescência (DVS alto)
        size = min(lai, 5.0) / 5.0
        senesce = max(0.0, (dvs - 1.6) / 0.6)            # 0..1 após DVS 1.6
        height = int(24 + size * 150 * (1 - 0.4 * senesce))
        if height < 10:
            height = 10

        # cor: verde saudável → marrom (estresse hídrico) / pálido (carência N)
        col = LEAF
        col = _lerp(col, LEAF_DRY, 1 - min(1.0, rftra))
        col = _lerp(col, LEAF_PALE, 1 - min(1.0, nni))
        col = _lerp(col, (150, 130, 40), senesce)        # amarela ao madurar

        top_y = base_y - height
        # caule
        pygame.draw.line(s, STEM, (x, base_y), (x, top_y), max(2, int(3 + size * 3)))

        # folhas: quantidade e tamanho conforme LAI
        n_leaves = 3 + int(size * 7)
        leaf_len = int(10 + size * 26)
        for k in range(n_leaves):
            ly = base_y - int(height * (0.2 + 0.75 * k / max(1, n_leaves - 1)))
            side = -1 if k % 2 == 0 else 1
            tip_x = x + side * leaf_len
            tip_y = ly - int(leaf_len * 0.35)
            pygame.draw.line(s, col, (x, ly), (tip_x, tip_y), max(2, int(2 + size * 3)))
            pygame.draw.circle(s, col, (tip_x, tip_y), max(3, int(4 + size * 6)))

        # floração/tuberização (DVS ~1.0-1.6): pequenas flores
        if 1.0 <= dvs <= 1.7 and size > 0.25:
            for k in range(3):
                fx = x + (k - 1) * 8
                fy = top_y + 6 + k * 4
                pygame.draw.circle(s, (245, 240, 200), (fx, fy), 3)

    def _draw_water_action(self, s, prog):
        random.seed(42)
        for _ in range(60):
            x = random.randint(0, self.W)
            y0 = random.randint(-self.ground_y, 0)
            y = int(y0 + prog * (self.ground_y + 200) * 1.3)
            if 0 <= y <= self.ground_y + 30:
                pygame.draw.line(s, WATER, (x, y), (x - 2, y + 10), 2)
                pygame.draw.circle(s, WATER, (x - 2, y + 10), 2)

    def _draw_nitrogen_action(self, s, prog):
        random.seed(99)
        for _ in range(28):
            x = random.randint(0, self.W)
            y0 = random.randint(-self.ground_y, 0)
            y = int(y0 + prog * (self.ground_y + 200) * 1.1)
            if 0 <= y <= self.ground_y + 24:
                pygame.draw.circle(s, PELLET, (x, y), 3)
                pygame.draw.circle(s, (60, 170, 70), (x + 1, y + 1), 1)

    def _draw_action_border(self, s, irrig, nkg, frame):
        if irrig <= 0 and nkg <= 0:
            return
        # pisca alternando entre as cores da ação
        on = (frame // 2) % 2 == 0
        if not on:
            return
        col = BANNER_WATER if irrig > 0 else BANNER_N
        if irrig > 0 and nkg > 0:
            col = ACCENT
        pygame.draw.rect(s, col, (0, 0, self.W, self.H), 8)

    def _draw_hud(self, s, day_index, sim_date, metrics):
        # painel translúcido no canto superior esquerdo
        panel = pygame.Surface((322, 196), pygame.SRCALPHA)
        panel.fill((*PANEL_BG, 205))
        s.blit(panel, (12, 12))

        x, y = 26, 22
        title = self.crop_name
        if self.location:
            title += f" — {self.location}"
        s.blit(self.f_title.render(title, True, ACCENT), (x, y)); y += 30

        dlabel = sim_date.strftime("%d/%m/%Y") if isinstance(sim_date, date) else str(sim_date)
        s.blit(self.f_big.render(dlabel, True, WHITE), (x, y)); y += 34

        dcount = f"Dia {day_index + 1}"
        if self.total_days:
            dcount += f" de {self.total_days}"
        dcount += " da simulação"
        s.blit(self.f_med.render(dcount, True, (180, 220, 255)), (x, y)); y += 30

        def stat(label, val, unit=""):
            nonlocal y
            txt = f"{label}: {val}{unit}"
            s.blit(self.f_small.render(txt, True, WHITE), (x, y)); y += 20

        stat("Estágio (DVS)", f"{_g(metrics,'DVS'):.2f}")
        stat("Folhagem (LAI)", f"{_g(metrics,'LAI'):.2f}")
        stat("Umidade solo (SM)", f"{_g(metrics,'SM'):.3f}")
        stat("Produção (TWSO)", f"{_g(metrics,'TWSO'):.0f}", " kg/ha")

    def _draw_action_banner(self, s, irrig, nkg):
        banners = []
        if irrig > 0:
            banners.append((BANNER_WATER, f"IRRIGAÇÃO   {irrig:.0f} mm"))
        if nkg > 0:
            banners.append((BANNER_N, f"NITROGÊNIO   {nkg:.0f} kg/ha"))
        if not banners:
            banners.append(((70, 70, 80), "Sem ação neste dia"))

        bh = 44
        total_h = bh * len(banners) + 6 * (len(banners) - 1)
        y0 = self.H - total_h - 16
        for i, (col, text) in enumerate(banners):
            y = y0 + i * (bh + 6)
            bw = 460
            x = (self.W - bw) // 2
            box = pygame.Surface((bw, bh), pygame.SRCALPHA)
            box.fill((*col, 235))
            s.blit(box, (x, y))
            pygame.draw.rect(s, WHITE, (x, y, bw, bh), 2)
            label = self.f_med.render(text, True, WHITE)
            s.blit(label, (x + (bw - label.get_width()) // 2,
                           y + (bh - label.get_height()) // 2))

    # ── emissão de quadros ──────────────────────────────────────────────────────
    def _emit_frame(self, gif=False):
        if self.window is not None:
            # janela ao vivo, se houver display
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pass
            self.window.blit(self.surface, (0, 0))
            pygame.display.flip()
            self.clock.tick(self.fps)

        arr = pygame.surfarray.array3d(self.surface)   # (W,H,3)
        arr = np.transpose(arr, (1, 0, 2))             # (H,W,3)
        if self._writer is not None:
            self._writer.append_data(arr)
        if gif and self.also_gif and self._imageio is not None:
            # quadro reduzido p/ o gif resumo (1 por dia)
            small = arr[::2, ::2, :].copy()
            self._gif_frames.append(small)

        # transmissão ao vivo: codifica JPEG e empurra p/ o navegador
        if self._live is not None and self._pil is not None:
            buf = io.BytesIO()
            self._pil.fromarray(arr).save(buf, format="JPEG", quality=80)
            self._live.update(buf.getvalue())
            # ritma em tempo real p/ a animação fluir no navegador
            self.clock.tick(self.fps)
