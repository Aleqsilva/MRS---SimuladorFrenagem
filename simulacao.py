class SimuladorPatio:
    def __init__(self):
        self.tempo_atual = 0
        self.passo_tempo = 0.1  # 100ms por frame
        self.paused = False

class VisualizadorPatio:
    def __init__(self, main_canvas, simulador):
        self.canvas = main_canvas
        self.simulador = simulador
        self.escala_pixels_por_metro = 0.5  # 1 metro = 0.5 pixels

        self.prog_inicial = None
        self.prog_final = None    

        self.margem_px = 50
        self.largura_px = 1064
        self.largura_util_px = self.largura_px - 2 * self.margem_px
        self.locacoes = {}
        self.sinais = {} 
        self.trens = {}

    def set_contexto_rota(self, prog_inicial, prog_final, locacoes, sinais):
        if float(prog_inicial) >= float(prog_final):
            raise ValueError("Progressiva inicial deve ser menor que a final.")
        
        self.prog_inicial = float(prog_inicial)
        self.prog_final = float(prog_final)
        self.desenhar_estrutura_estatica(locacoes, sinais)

    def progressiva_para_x(self, progressiva_m):
        if self.prog_final is None or self.prog_inicial is None:
            raise ValueError("Contexto de rota nao definido.")
        span = self.prog_final - self.prog_inicial
        t = (float(progressiva_m) - self.prog_inicial) / span
        t = max(0.0, min(1.0, t))
        return self.margem_px + t * self.largura_util_px

    def metros_para_pixels(self, metros):
        if self.prog_final is None or self.prog_inicial is None:
            raise ValueError("Contexto de rota nao definido.")
        span_m = max(1e-9, float(self.prog_final) - float(self.prog_inicial))
        escala_px_por_m = float(self.largura_util_px) / span_m
        return float(metros) * escala_px_por_m

    def desenhar_estrutura_estatica(self, locacoes, sinais):
        if not self.canvas:
            return
        
        self.canvas.delete("patio_static")
        self.locacoes = {}
        self.sinais = {}

        try:
            largura_canvas = int(self.canvas.winfo_width())
        except Exception:
            largura_canvas = self.largura_px

        if largura_canvas <= 1:
            largura_canvas = self.largura_px

        try:
            altura_canvas = int(self.canvas.winfo_height())
        except Exception:
            altura_canvas = 553

        if altura_canvas <= 1:
            altura_canvas = 553

        self.largura_px = largura_canvas
        self.largura_util_px = max(100, int(self.largura_px * 0.84))
        self.margem_px = max(20, int((self.largura_px - self.largura_util_px) / 2))

        self.trilho_y = int(altura_canvas * 0.46)
        self.locacao_top = self.trilho_y + 20
        self.locacao_bottom = self.trilho_y + 50
        self.sinal_cabeca_raio = 8
        self.sinal_cabeca_cy = self.trilho_y - 24
        self.sinal_haste_top = self.sinal_cabeca_cy + self.sinal_cabeca_raio
        self.sinal_haste_bottom = self.trilho_y

        x_ini_trilho = self.margem_px
        x_fim_trilho = self.margem_px + self.largura_util_px

        self.canvas.create_line(
            x_ini_trilho,
            self.trilho_y,
            x_fim_trilho,
            self.trilho_y,
            width=4,
            fill="#444444",
            tags=("patio_static", "trilho")
        )

        self.canvas.create_text(
            x_ini_trilho - 20,
            self.trilho_y + 20,
            text=f"{self.prog_inicial:.1f} m",
            anchor="w",
            fill="#555555",
            tags=("patio_static",)
        )
        self.canvas.create_text(
            x_fim_trilho + 20,
            self.trilho_y + 20,
            text=f"{self.prog_final:.1f} m",
            anchor="e",
            fill="#555555",
            tags=("patio_static",)
        )

        for loc in locacoes:
            loc_id = str(loc.get("id", "LOC"))
            loc_label = str(loc.get("label", loc_id))
            p0 = float(loc.get("prog_inicio", self.prog_inicial))
            p1 = float(loc.get("prog_fim", self.prog_final))
            if p1 < p0:
                p0, p1 = p1, p0

            x0 = self.progressiva_para_x(p0)
            x1 = self.progressiva_para_x(p1)
            if abs(x1 - x0) < 4:
                x1 = x0 + 4

            rect_id = self.canvas.create_rectangle(
                x0,
                self.locacao_top + 10,
                x1,
                self.locacao_bottom + 10,
                outline="#1f4e79",
                width=2,
                fill="#dbeafe",
                tags=("patio_static", "locacao")
            )
            label_id = self.canvas.create_text(
                (x0 + x1) / 2,
                self.locacao_bottom - 3,
                text=loc_label,
                fill="#1f4e79",
                tags=("patio_static", "locacao_label")
            )

            self.locacoes[loc_id] = {
                "rect_id": rect_id,
                "label_id": label_id,
                "prog_inicio": p0,
                "prog_fim": p1
            }

        cor_estado = {
            "VERDE": "#22c55e",
            "AMARELO": "#eab308",
            "VERMELHO": "#ef4444"
        }

        for sig in sinais:
            sig_id = str(sig.get("id", "S"))
            pos = float(sig.get("posicao", self.prog_inicial))
            estado = str(sig.get("estado", "VERMELHO")).upper()
            fill = cor_estado.get(estado, "#9ca3af")

            x = self.progressiva_para_x(pos)
            haste_id = self.canvas.create_line(
                x,
                self.sinal_haste_top,
                x,
                self.sinal_haste_bottom,
                width=3,
                fill="#555555",
                tags=("patio_static", "sinal_haste")
            )
            cabeca_id = self.canvas.create_oval(
                x - self.sinal_cabeca_raio,
                self.sinal_cabeca_cy - self.sinal_cabeca_raio,
                x + self.sinal_cabeca_raio,
                self.sinal_cabeca_cy + self.sinal_cabeca_raio,
                outline="#333333",
                width=1,
                fill=fill,
                tags=("patio_static", "sinal_cabeca")
            )
            label_id = self.canvas.create_text(
                x,
                self.sinal_cabeca_cy - self.sinal_cabeca_raio - 10,
                text=sig_id,
                fill="#333333",
                tags=("patio_static", "sinal_label")
            )

            self.sinais[sig_id] = {
                "haste_id": haste_id,
                "cabeca_id": cabeca_id,
                "label_id": label_id,
                "posicao": pos,
                "estado": estado
            }

    def registrar_trem(self, trem_id, cor="blue", comprimento_visual_px=30, comprimento_m=None, crescente=True, progressiva_inicial_m=None):
        # Desenha o trem na simualação
        if self.canvas is None:
            return None

        if self.prog_inicial is None or self.prog_final is None:
            raise ValueError("Contexto de rota nao definido para registrar trem.")

        if comprimento_m is not None:
            comprimento_px = max(12.0, self.metros_para_pixels(float(comprimento_m)))
        else:
            comprimento_px = float(comprimento_visual_px)
    
        # A progressiva representa a frente da locomotiva (cabeca do trem).
        if progressiva_inicial_m is not None:
            x_frente = self.progressiva_para_x(float(progressiva_inicial_m))
        else:
            x_frente = self.margem_px if crescente else (self.margem_px + self.largura_util_px)

        # No sentido crescente, a frente fica no lado direito do retangulo.
        # No sentido decrescente, a frente fica no lado esquerdo do retangulo.
        if crescente:
            x_ini = x_frente - comprimento_px
            x_fim = x_frente
        else:
            x_ini = x_frente
            x_fim = x_frente + comprimento_px
        y_top = self.trilho_y - 8
        y_bot = self.trilho_y + 8

        rect_id = self.canvas.create_rectangle(
            x_ini,
            y_top,
            x_fim,
            y_bot,
            outline="#000000",
            width=2,
            fill=cor,
            tags=("trem", trem_id)
        )
        
        label_id = self.canvas.create_text(
            (x_ini + x_fim) / 2.0,
            self.trilho_y,
            text=trem_id[:3],
            fill="white",
            font=("Arial", 8, "bold"),
            tags=("trem_label", trem_id)
        )

        if not hasattr(self, "trens"):
            self.trens = {}

        self.trens[trem_id] = {
            "rect_id": rect_id,
            "label_id": label_id,
            "cor": cor,
            "cor_base": cor,
            "comprimento_px": comprimento_px,
            "posicao_x_atual": x_frente  # posicao da frente (locomotiva)
        }

        return rect_id

    def atualizar_frame(self, frame):
        """Atualiza a posição dos trens e o estado dos sinais
        frame: {
            "tempo_s": float,
            "trens": [{"id": str, "progressiva_m": float}, ...],
            "sinais": [{"id": str, "estado": str}, ...],
            "locacoes": [{"id": str, "ocupante_trem_id": str or None}, ...]
        }
        """
        if not frame or not self.canvas:
            return

        frame_trens = frame.get("trens", [])
        frame_trens_ids = {str(t.get("id", "")) for t in frame_trens if str(t.get("id", ""))}

        # Trens ausentes no frame atual ficam ocultos, evitando sobras visuais
        # no reset e permitindo reaparecimento em frames futuros.
        for trem_id, trem_info in self.trens.items():
            visivel = trem_id in frame_trens_ids
            estado_item = "normal" if visivel else "hidden"
            self.canvas.itemconfigure(trem_info["rect_id"], state=estado_item)
            self.canvas.itemconfigure(trem_info["label_id"], state=estado_item)
        
        for trem_data in frame_trens:
            trem_id = str(trem_data.get("id", ""))
            prog_m = float(trem_data.get("progressiva_m", self.prog_inicial))
            status = str(trem_data.get("status_operacional", ""))
            bloqueado = bool(trem_data.get("bloqueado", False))

            if trem_id not in self.trens:
                # Caso um trem apareca sem pre-registro, cria em tempo de execucao.
                self.registrar_trem(trem_id=trem_id)
                if trem_id not in self.trens:
                    continue
            
            x_novo = self.progressiva_para_x(prog_m)
            trem_info = self.trens[trem_id]
            self.canvas.itemconfigure(trem_info["rect_id"], state="normal")
            self.canvas.itemconfigure(trem_info["label_id"], state="normal")
            x_atual = trem_info["posicao_x_atual"]
            dx = x_novo - x_atual

            self.canvas.move(trem_info["rect_id"], dx, 0)
            self.canvas.move(trem_info["label_id"], dx, 0)
            trem_info["posicao_x_atual"] = x_novo

            # Cores visuais por estado operacional do trem.
            if bloqueado or status in ("AGUARDANDO", "AGUARDANDO_AUTORIZACAO"):
                cor_trem = "#f59e0b"
            elif status in ("PARADO", "PARADO_LIBERADO"):
                cor_trem = "#9ca3af"
            elif status == "EM_SAIDA":
                cor_trem = "#38bdf8"
            else:
                cor_trem = trem_info.get("cor_base", trem_info.get("cor", "blue"))
            self.canvas.itemconfig(trem_info["rect_id"], fill=cor_trem)

        for sinal_data in frame.get("sinais", []):
            sinal_id = str(sinal_data.get("id", ""))
            estado = str(sinal_data.get("estado", "VERMELHO")).upper()

            if sinal_id not in self.sinais:
                continue

            cor_estado = {
                "VERDE": "#22c55e",
                "AMARELO": "#eab308",
                "VERMELHO": "#ef4444"
            }

            nova_cor = cor_estado.get(estado, "#9ca3af")
            sinal_info = self.sinais[sinal_id]
            cabeca_id = sinal_info.get("cabeca_id")
            if cabeca_id is None:
                cabeca_id = sinal_info.get("oval_id")
            if cabeca_id is not None:
                self.canvas.itemconfig(cabeca_id, fill=nova_cor)
            self.sinais[sinal_id]["estado"] = estado

        conflito = bool(frame.get("conflito_ocupacao", False))
        bloqueados = frame.get("bloqueados", [])

        for loc_data in frame.get("locacoes", []):
            loc_id = str(loc_data.get("id", ""))
            ocupante = loc_data.get("ocupante_trem_id")
            
            if loc_id not in self.locacoes:
                continue
            
            loc_info = self.locacoes[loc_id]
            fill = "#fca5a5" if ocupante else "#dbeafe"
            outline = "#1f4e79"
            width = 2

            if conflito:
                outline = "#b91c1c"   # vermelho forte
                width = 4
            elif bloqueados:
                outline = "#d97706"  # laranja de espera
                width = 3

            self.canvas.itemconfig(loc_info["rect_id"], fill=fill, outline=outline, width=width)
                
        if not hasattr(self, "alerta_id"):
            self.alerta_id = self.canvas.create_text(
                12, 12, anchor="nw", text="", fill="#b91c1c", font=("Arial", 10, "bold")
            )

        if frame.get("conflito_ocupacao", False):
            ocup = ", ".join(frame.get("ocupantes", []))
            self.canvas.itemconfig(self.alerta_id, text=f"CONFLITO DE OCUPACAO: {ocup}")
        elif frame.get("bloqueados", []):
            aguardando = ", ".join(frame.get("bloqueados", []))
            self.canvas.itemconfig(self.alerta_id, text=f"AGUARDANDO LOCACAO: {aguardando}")
        else:
            self.canvas.itemconfig(self.alerta_id, text="")

        # Forçar redraw
        self.canvas.update_idletasks()

class ControladorSimulacao:
    def __init__(self, visualizador, root=None, on_finish=None):
        self.visualizador = visualizador
        self.root = root  # Referência à janela principal do Tkinter, se necessário
        self.on_finish = on_finish

        self.frames = []
        self.frame_atual = 0
        self.estado = "idle"  # idle, running, paused, stopped
        self.velocidade = 1.0
        self.intervalo_ms = 150
        self.after_id = None
    
    def carregar_replay(self, frames):
        self.frames = frames
        self.frame_atual = 0
        self.estado = "idle"

    def play(self):
        if self.estado == "running":
            return

        if not self.frames:
            self.estado = "idle"
            return
        
        if self.estado == "paused":
            self.estado = "running"
            self._proximo_frame()
        elif self.estado in ["idle", "stopped"]:
            self.estado = "running"
            self.frame_atual = 0
            self._proximo_frame()

    def pause(self):
        if self.estado == "running":
            self.estado = "paused"
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None

    def stop_reset(self):
        "Para e volta ao frame inicial."
        self.set_velocidade(1.0)
        self.estado = "stopped"
        self.frame_atual = 0
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        
        if self.frames:
            self.visualizador.atualizar_frame(self.frames[0])
    
    def set_velocidade(self, fator):
        "Define velocidade do replay"
        self.velocidade = float(fator)
        if self.estado == "running" and self.after_id:
            self.root.after_cancel(self.after_id)
            self._proximo_frame()

    def ir_para_frame(self, indice):
        "Posiciona o replay em um frame específico sem reiniciar." 
        if not self.frames:
            return

        try:
            idx = int(indice)
        except Exception:
            idx = 0

        idx = max(0, min(len(self.frames) - 1, idx))

        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.estado = "paused"
        self.visualizador.atualizar_frame(self.frames[idx])
        # frame_atual aponta para o próximo frame a ser exibido no play.
        self.frame_atual = idx + 1

    def _proximo_frame(self):
        """Renderiza próximo frame e agenda o próximo."""
        if self.estado != "running" or not self.frames:
            return
        
        if self.frame_atual < len(self.frames):
            frame = self.frames[self.frame_atual]
            self.visualizador.atualizar_frame(frame)
            self.frame_atual += 1
            
            # Agendar próximo frame com base em velocidade
            intervalo_ajustado = int(self.intervalo_ms / self.velocidade)
            self.after_id = self.root.after(intervalo_ajustado, self._proximo_frame)
        else:
            # Fim da animação
            self.estado = "idle"
            self.frame_atual = len(self.frames)
            if callable(self.on_finish):
                self.on_finish()

def gerar_frames_sinteticos(trem_id="T1", prog_ini=454180, prog_fim=455200, num_frames=40):
    """Gera frames sintéticos para teste sem precisar de pipeline real."""
    frames = []
    for i in range(num_frames):
        t = float(i) / float(num_frames - 1) if num_frames > 1 else 0.0
        prog = prog_ini + t * (prog_fim - prog_ini)
        
        frame = {
            "tempo_s": float(i) * 0.5,
            "trens": [{"id": trem_id, "progressiva_m": prog}],
            "sinais": [
                {"id": "S_A", "posicao": 454700, "estado": "AMARELO" if i < 15 else "VERMELHO"},
                {"id": "S_B", "posicao": 455200, "estado": "VERMELHO"}
            ],
            "locacoes": [
                {"id": "LOC_A", "ocupante_trem_id": trem_id if prog_ini <= prog < (prog_ini + 520) else None},
                {"id": "LOC_B", "ocupante_trem_id": trem_id if (prog_ini + 520) <= prog <= prog_fim else None}
            ]
        }
        frames.append(frame)
    
    return frames

def __main__():
    import tkinter as tk
    from tkinter import ttk
    
    # Criar janela Tkinter
    root = tk.Tk()
    root.title("Simulador de Patio - com Controles")
    root.geometry("1100x450")
    
    # Frame superior: canvas
    frame_canvas = ttk.Frame(root)
    frame_canvas.pack(pady=10, padx=10, fill="both", expand=True)
    
    canvas = tk.Canvas(frame_canvas, width=1100, height=260, bg="white")
    canvas.pack()
    
    # Instanciar visualizador e controlador
    simulador = SimuladorPatio()
    visualizador = VisualizadorPatio(main_canvas=canvas, simulador=simulador)
    controlador = ControladorSimulacao(visualizador=visualizador, root=root)
    
    # Dados de teste
    locacoes = [
        {"id": "LOC_A", "prog_inicio": 454180, "prog_fim": 454700},
        {"id": "LOC_B", "prog_inicio": 454700, "prog_fim": 455200}
    ]
    sinais = [
        {"id": "S_A", "posicao": 454700, "estado": "AMARELO"},
        {"id": "S_B", "posicao": 455200, "estado": "VERMELHO"}
    ]
    
    # Desenhar estrutura estática
    visualizador.set_contexto_rota(
        prog_inicial=454000, 
        prog_final=455500, 
        locacoes=locacoes, 
        sinais=sinais
    )
    
    # Registrar 1 trem
    visualizador.registrar_trem(trem_id="T1", cor="blue", comprimento_visual_px=35)
    
    # Gerar frames
    frames = gerar_frames_sinteticos(
        trem_id="T1",
        prog_ini=454180,
        prog_fim=455200,
        num_frames=40
    )
    controlador.carregar_replay(frames)
    
    # Frame inferior: controles
    frame_controles = ttk.Frame(root)
    frame_controles.pack(pady=10, padx=10, fill="x")
    
    # Label de status
    status_label = tk.Label(frame_controles, text="Estado: Pronto | Frame: 0/40 | Tempo: 0.0s", 
                            fg="blue", font=("Arial", 10))
    status_label.pack(side="top", pady=5)
    
    def atualizar_status():
        """Atualiza label de status."""
        if controlador.frames:
            frame = controlador.frames[min(controlador.frame_atual - 1, len(controlador.frames) - 1)]
            tempo = frame.get("tempo_s", 0)
            prog = frame["trens"][0]["progressiva_m"] if frame["trens"] else 0
            status = f"Estado: {controlador.estado.upper()} | Frame: {controlador.frame_atual}/{len(controlador.frames)} | Tempo: {tempo:.1f}s | Prog: {prog:.1f}m"
        else:
            status = "Sem frames carregados"
        status_label.config(text=status)
    
    # Botões de controle
    frame_botoes = ttk.Frame(frame_controles)
    frame_botoes.pack(side="top", pady=5)
    
    btn_play = tk.Button(
        frame_botoes, 
        text="▶ Play", 
        command=lambda: (controlador.play(), atualizar_status()),
        bg="lightgreen",
        width=12
    )
    btn_play.pack(side="left", padx=5)
    
    btn_pause = tk.Button(
        frame_botoes,
        text="⏸ Pause",
        command=lambda: (controlador.pause(), atualizar_status()),
        bg="lightyellow",
        width=12
    )
    btn_pause.pack(side="left", padx=5)
    
    btn_reset = tk.Button(
        frame_botoes,
        text="⏹ Stop/Reset",
        command=lambda: (controlador.stop_reset(), visualizador.atualizar_frame(frames[0]), atualizar_status(), controlador.set_velocidade(1.0)),
        bg="lightcoral",
        width=12
    )
    btn_reset.pack(side="left", padx=5)
    
    # Velocidades
    frame_velocidades = ttk.Frame(frame_controles)
    frame_velocidades.pack(side="top", pady=5)
    
    tk.Label(frame_velocidades, text="Velocidade:", font=("Arial", 10)).pack(side="left", padx=5)
    
    btn_vel_050 = tk.Button(
        frame_velocidades,
        text="0.5x",
        command=lambda: (controlador.set_velocidade(0.5), atualizar_status()),
        width=8
    )
    btn_vel_050.pack(side="left", padx=3)
    
    btn_vel_100 = tk.Button(
        frame_velocidades,
        text="1.0x",
        command=lambda: (controlador.set_velocidade(1.0), atualizar_status()),
        width=8,
        bg="lightblue"
    )
    btn_vel_100.pack(side="left", padx=3)
    
    btn_vel_200 = tk.Button(
        frame_velocidades,
        text="2.0x",
        command=lambda: (controlador.set_velocidade(2.0), atualizar_status()),
        width=8
    )
    btn_vel_200.pack(side="left", padx=3)
    
    # Loop para atualizar status a cada frame
    def loop_atualizar():
        atualizar_status()
        root.after(50, loop_atualizar)
    
    loop_atualizar()
    
    root.mainloop()

if __name__ == "__main__":
    __main__()