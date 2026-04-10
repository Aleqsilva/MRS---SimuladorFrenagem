from simulacao import VisualizadorPatio, SimuladorPatio, ControladorSimulacao
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import pipeline
import grade
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
from matplotlib.ticker import MultipleLocator, AutoMinorLocator, FixedLocator
import numpy as np
import csv
import os
import json, uuid, hashlib, platform, sys
from datetime import datetime
from tkinter import simpledialog

class LocalizacaoUI:
    """Interface para uma locação individual dentro do notebook"""
    def __init__(self, parent_notebook, locacao_id, locacao_nome="Nova Locação", main_app=None):
        self.locacao_id = locacao_id
        self.locacao_nome = locacao_nome
        self.main_app = main_app
        self.results = None
        self.resumo = None
        self.last_params = None
        self.csv_fullpath = None
        self._after_telemetria = None
        self._after_alerta = None
        self.replay_finalizado = False
        self._velocidade_selecionada = 1.0
        self._run_token = 0
        self._timeline_syncing = False
        self._timeline_meta = {"x0": 92, "x1": 300, "tempo_final": 0.0}
        self._timeline_playhead_id = None
        self._timeline_eventos_por_trem = {}
        self._animacao_inicializada = False
        self.modo_livre = False
        self.var_progressiva_final_livre = tk.StringVar(value="-")
        self.vmas_livre = []
        self.pausas_livre = []

        # Create main frame para esta locação
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text=locacao_nome)
        
        # Layout base: 2 colunas (inputs | resultados)
        self.frame.columnconfigure(0, weight=0)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)
        
        # --- PAINEL DE INPUTS --- 
        self.frame_inputs = ttk.LabelFrame(self.frame, text="Parâmetros - " + locacao_nome)
        self.frame_inputs.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        self.frame_inputs.columnconfigure(0, weight=0)
        self.frame_inputs.columnconfigure(1, weight=1)
        
        # --- PAINEL DE RESULTADOS ---
        self.frame_results = ttk.Frame(self.frame)
        self.frame_results.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.frame_results.columnconfigure(0, weight=1)
        self.frame_results.rowconfigure(1, weight=1)
        
        self.label = ttk.Label(self.frame_results, text=f"Simulação - {locacao_nome}", font=("Arial", 16, "bold"))
        self.label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Criar inputs
        r = 0
        self.entry_progressiva = self._cria_entry_label(self.frame_inputs, "Progressiva Inicial (m):", row=r, default=454180); r += 1
        self.entry_nome_sinal_a = self._cria_entry_label(self.frame_inputs, "Nome Sinal A:", row=r, default="Sinal A"); r += 1
        ttk.Separator(self.frame_inputs, orient='horizontal').grid(row=r, column=0, columnspan=2, sticky="ew", pady=(6, 0)); r += 1
        self.entry_ponto_a_proteger = self._cria_entry_label(self.frame_inputs, "Ponto a Proteger (m):", row=r, default=455551); r += 1
        self.entry_nome_sinal_b = self._cria_entry_label(self.frame_inputs, "Nome Sinal B:", row=r, default="Sinal B"); r += 1
        ttk.Separator(self.frame_inputs, orient='horizontal').grid(row=r, column=0, columnspan=2, sticky="ew", pady=(6, 0)); r += 1
        self.entry_velocidade_inicial = self._cria_entry_label(self.frame_inputs, "Velocidade Inicial (km/h):", row=r, default=30.0); r += 1
        self.entry_tempo_freio_minimo = self._cria_entry_label(self.frame_inputs, "Tempo de Freio Mínimo (s):", row=r, default=185.0); r += 1
        self.entry_tempo_equalizacao = self._cria_entry_label(self.frame_inputs, "Tempo de Equalização do Freio (s):", row=r, default=192.6); r += 1
        self.entry_tempo_parado = self._cria_entry_label(self.frame_inputs, "Tempo Parado (T_parado, s):", row=r, default=5.0); r += 1
        self.entry_qtd_trens = self._cria_entry_label(self.frame_inputs, "Quantidade de Trens:", row=r, default=1); r += 1
        self.entry_taxa_frenagem = self._cria_entry_label(self.frame_inputs, "Taxa de Frenagem (m/s²):", row=r, default=-0.040); r += 1
        self.entry_tamanho_trem = self._cria_entry_label(self.frame_inputs, "Tamanho do Trem (m):", row=r, default=1108); r += 1
        self.entry_vma_saida = self._cria_entry_label(self.frame_inputs, "VMA Saída (km/h):", row=r, default=60.0); r += 1
        self.entry_step = self._cria_entry_label(self.frame_inputs, "Step (m):", row=r, default=10); r += 1
        self.entry_csv = self._cria_entry_label(self.frame_inputs, "Arquivo CSV:", row=r, default="dados454_teste.csv"); r += 1
        self.csv_button = self._cria_botao(self.frame_inputs, "Selecionar CSV", self.selecionar_csv, row=r); r += 1
        
        self.check_var = tk.BooleanVar(value=True)
        self.checkbutton_crescente = ttk.Checkbutton(self.frame_inputs, text="Sentido Crescente", variable=self.check_var)
        self.checkbutton_crescente.grid(row=r, column=0, columnspan=2, sticky="w", pady=(6, 0)); r += 1
        
        self.botao_rodar = self._cria_botao(self.frame_inputs, "Rodar Simulação", self.on_button_click, row=r); r += 1
        self.botao_exportar = self._cria_botao(self.frame_inputs, "Exportar", self.exportar, row=r); r += 1
        
        # Notebook para resultados desta locação
        self.notebook = ttk.Notebook(self.frame_results)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        
        self.aba_tabela_corrida = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_tabela_corrida, text="Tabela Corrida")

        self.aba_graficos = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_graficos, text="Gráficos de Corrida e Grade")
        self.aba_corrida = self.aba_graficos
        self.aba_grade = self.aba_graficos

        self.aba_diagrama = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_diagrama, text="Diagrama Espaço-Tempo")
        
        self.aba_animacao = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_animacao, text="Animação")

        self.aba_animacao.columnconfigure(0, weight=1)
        self.aba_animacao.rowconfigure(0, weight=1)
        self.aba_animacao.rowconfigure(2, weight=0)
        self.aba_animacao.rowconfigure(3, weight=0)

        self.canvas_animacao = tk.Canvas(self.aba_animacao, bg="white", height=260)
        self.canvas_animacao.grid(row=0, column=0, sticky="nsew")


        # Configure expansão das abas
        for tab in (self.aba_tabela_corrida, self.aba_diagrama, self.aba_graficos):
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)

        self.aba_graficos.columnconfigure(0, weight=1)
        self.aba_graficos.columnconfigure(1, weight=1)
        self.aba_graficos.rowconfigure(0, weight=1)
        
        # Plot Grade
        self.fig_grade = Figure(figsize=(6, 4), dpi=100)
        self.ax_grade = self.fig_grade.add_subplot(111)
        self.canvas_grade = FigureCanvasTkAgg(self.fig_grade, master=self.aba_graficos)
        self.canvas_grade.get_tk_widget().grid(row=0, column=1, sticky="nsew")

        # Diagrama Espaco-Tempo
        self.fig_diagrama = Figure(figsize=(6, 4), dpi=100)
        self.ax_diagrama = self.fig_diagrama.add_subplot(111)
        self.canvas_diagrama = FigureCanvasTkAgg(self.fig_diagrama, master=self.aba_diagrama)
        self.canvas_diagrama.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Plot Corrida
        self.fig_corrida = Figure(figsize=(6, 4), dpi=100)
        self.ax_corrida = self.fig_corrida.add_subplot(111)
        self.canvas_corrida = FigureCanvasTkAgg(self.fig_corrida, master=self.aba_graficos)
        self.canvas_corrida.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Aba Tabela
        self.aba_tabela_corrida.rowconfigure(0, weight=0)
        self.aba_tabela_corrida.rowconfigure(1, weight=1)
        self.aba_tabela_corrida.columnconfigure(0, weight=1)
        
        self.frame_resumo = ttk.Frame(self.aba_tabela_corrida)
        self.frame_resumo.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        
        self.ax_corrida_prog = self.ax_corrida.twinx()
        self.var_prog_parada = tk.StringVar(value="-")
        self.var_tempo_total = tk.StringVar(value="-")
        self.var_dist_perc = tk.StringVar(value="-")
        self.var_dist_protecao = tk.StringVar(value="-")
        self.var_dist_sinais = tk.StringVar(value="-")
        self.var_vel_med = tk.StringVar(value="-")
        self.var_headway = tk.StringVar(value="-")
        self.var_cap_teor = tk.StringVar(value="-")
        self.var_cap_prat = tk.StringVar(value="-")
        
        ttk.Label(self.frame_resumo, text="Progressiva parada:*").grid(row=0, column=0, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_prog_parada).grid(row=0, column=1, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Tempo de Ocupação (s):").grid(row=0, column=2, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_tempo_total).grid(row=0, column=3, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Tempo de Headway (s):").grid(row=0, column=4, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_headway).grid(row=0, column=5, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Capacidade Teórica (trens/h):").grid(row=0, column=6, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_cap_teor).grid(row=0, column=7, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Capacidade Prática (trens/h):").grid(row=1, column=6, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_cap_prat).grid(row=1, column=7, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Distância percorrida (m):").grid(row=1, column=0, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_dist_perc).grid(row=1, column=1, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Distância de proteção (m):").grid(row=1, column=2, sticky="w")
        self.lbl_dist_protecao = ttk.Label(self.frame_resumo, textvariable=self.var_dist_protecao)
        self.lbl_dist_protecao.grid(row=1, column=3, sticky="w", padx=(6, 20))
        
        ttk.Label(self.frame_resumo, text="Distância entre sinais (m):").grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(self.frame_resumo, textvariable=self.var_dist_sinais).grid(row=2, column=1, sticky="w", padx=(6, 20), pady=(4, 0))
        
        ttk.Label(self.frame_resumo, text="Velocidade Média (m/s):").grid(row=2, column=2, sticky="w")
        ttk.Label(self.frame_resumo, textvariable=self.var_vel_med).grid(row=2, column=3, sticky="w", padx=(6, 20))
        
        tk.Label(self.frame_resumo, text="*O valor de parada da Progressiva pode variar em relação ao sinal final devido a diferença de Km histórico e real", fg="gray", font=("Arial", 9, "italic")).grid(row=2, column=4, columnspan=4, sticky="w", pady=(4, 0))
        
        self.tabela_corrida = ttk.Treeview(
            self.aba_tabela_corrida,
            columns=("Tempo", "Velocidade Km/h", "Progressiva", "Aceleração", "Variação de Aceleração"),
            show="headings",
        )
        self.tabela_corrida.heading("Tempo", text="Tempo (s)")
        self.tabela_corrida.heading("Velocidade Km/h", text="Velocidade (km/h)")
        self.tabela_corrida.heading("Progressiva", text="Progressiva (m)")
        self.tabela_corrida.heading("Aceleração", text="Aceleração (m/s²)")
        self.tabela_corrida.heading("Variação de Aceleração", text="Variação de Aceleração (m/s³)")
        
        self.tabela_corrida.column("Tempo", width=50, anchor="center")
        self.tabela_corrida.column("Velocidade Km/h", width=80, anchor="center")
        self.tabela_corrida.column("Progressiva", width=80, anchor="center")
        self.tabela_corrida.column("Aceleração", width=80, anchor="center")
        self.tabela_corrida.column("Variação de Aceleração", width=100, anchor="center")

        self.tabela_corrida.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        
        self.scroll_tabela_corrida = ttk.Scrollbar(self.aba_tabela_corrida, orient=tk.VERTICAL, command=self.tabela_corrida.yview)
        self.tabela_corrida.configure(yscrollcommand=self.scroll_tabela_corrida.set)
        self.scroll_tabela_corrida.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
    
        self.frame_ctrl_anim = ttk.Frame(self.aba_animacao)
        self.frame_ctrl_anim.grid(row=1, column=0, sticky="ew", pady=6)

        self.btn_play = tk.Button(self.frame_ctrl_anim, text="▶ Play", command=self._play_replay, bd=2, width=6)
        self.btn_play.pack(side="left", padx=4)
        self.btn_pause = tk.Button(self.frame_ctrl_anim, text="⏸ Pause", command=self._pause_replay, bd=2, width=7)
        self.btn_pause.pack(side="left", padx=4)
        self.btn_reset = tk.Button(self.frame_ctrl_anim, text="⏹ Reset", command=self._reset_replay, bd=2, width=8)
        self.btn_reset.pack(side="left", padx=4)
        
        separator = ttk.Separator(self.frame_ctrl_anim, orient='vertical')
        separator.pack(side="left", fill="y", padx=8)

        self.btn_vel_05 = tk.Button(self.frame_ctrl_anim, text="0.5x", command=lambda: self._definir_velocidade_replay(0.5), bd=2)
        self.btn_vel_05.pack(side="left", padx=4)
        self.btn_vel_10 = tk.Button(self.frame_ctrl_anim, text="1.0x", command=lambda: self._definir_velocidade_replay(1.0), bd=2)
        self.btn_vel_10.pack(side="left", padx=4)
        self.btn_vel_20 = tk.Button(self.frame_ctrl_anim, text="2.0x", command=lambda: self._definir_velocidade_replay(2.0), bd=2)
        self.btn_vel_20.pack(side="left", padx=4)

        self._atualizar_destaque_velocidade()

        self.var_alerta_anim = tk.StringVar(value="")
        ttk.Label(self.frame_ctrl_anim, textvariable=self.var_alerta_anim, foreground="#b91c1c").pack(side="left", padx=12)

        self.var_info_realtime = tk.StringVar(value="Vel: 1.0x | Tempo: 0.0s | Progresso: 0.0% | Trem: -")
        ttk.Label(self.frame_ctrl_anim, textvariable=self.var_info_realtime, foreground="#0f172a").pack(side="right", padx=8)

        self.frame_info_anim = ttk.LabelFrame(self.aba_animacao, text="Telemetria dos Trens")
        self.frame_info_anim.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.frame_info_anim.columnconfigure(0, weight=1)
        self.frame_info_anim.rowconfigure(0, weight=1)

        self.tabela_telemetria = ttk.Treeview(
            self.frame_info_anim,
            columns=("Trem", "Status", "Velocidade", "Progressiva", "Aceleração"),
            show="headings",
            height=4,
        )
        self.tabela_telemetria.heading("Trem", text="Trem")
        self.tabela_telemetria.heading("Status", text="Status")
        self.tabela_telemetria.heading("Velocidade", text="Velocidade (km/h)")
        self.tabela_telemetria.heading("Progressiva", text="Progressiva (m)")
        self.tabela_telemetria.heading("Aceleração", text="Aceleração (m/s²)")

        self.tabela_telemetria.column("Trem", width=60, anchor="center")
        self.tabela_telemetria.column("Status", width=80, anchor="center")
        self.tabela_telemetria.column("Velocidade", width=60, anchor="center")
        self.tabela_telemetria.column("Progressiva", width=60, anchor="center")
        self.tabela_telemetria.column("Aceleração", width=60, anchor="center")
        self.tabela_telemetria.grid(row=0, column=0, sticky="nsew")

        self.scroll_tabela_telemetria = ttk.Scrollbar(self.frame_info_anim, orient=tk.VERTICAL, command=self.tabela_telemetria.yview)
        self.tabela_telemetria.configure(yscrollcommand=self.scroll_tabela_telemetria.set)
        self.scroll_tabela_telemetria.grid(row=0, column=1, sticky="ns")

        self.frame_timeline = ttk.LabelFrame(self.aba_animacao, text="Timeline Replay")
        self.frame_timeline.grid(row=3, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.frame_timeline.columnconfigure(0, weight=1)
        self.frame_timeline.rowconfigure(1, weight=1)

        self.var_timeline = tk.DoubleVar(value=0.0)
        self.scale_timeline = tk.Scale(
            self.frame_timeline,
            from_=0,
            to=0,
            orient="horizontal",
            variable=self.var_timeline,
            showvalue=0,
            resolution=1,
            command=self._on_timeline_change,
            length=820,
        )
        self.scale_timeline.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 2))

        # Frame intermédio para conter canvas + scrollbar (permite scroll vertical)
        self.frame_timeline_scroll = ttk.Frame(self.frame_timeline)
        self.frame_timeline_scroll.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 4))
        self.frame_timeline_scroll.columnconfigure(0, weight=1)
        self.frame_timeline_scroll.rowconfigure(0, weight=1)

        self.canvas_timeline_marks = tk.Canvas(self.frame_timeline_scroll, height=100, bg="white", highlightthickness=0)
        self.canvas_timeline_marks.grid(row=0, column=0, sticky="nsew")

        # Scrollbar vertical para timeline
        self.scrollbar_timeline = ttk.Scrollbar(self.frame_timeline_scroll, orient=tk.VERTICAL, command=self.canvas_timeline_marks.yview)
        self.scrollbar_timeline.grid(row=0, column=1, sticky="ns")
        self.canvas_timeline_marks.configure(yscrollcommand=self.scrollbar_timeline.set)

        # Configurar altura máxima para a timeline (em número de trens visíveis)
        self.max_altura_timeline = 170  # pixels
        self.altura_por_trem_timeline = 18  # pixels por trem

        # Bind mouse wheel para scroll no canvas_timeline_marks
        self.canvas_timeline_marks.bind("<MouseWheel>", self._on_canvas_timeline_scroll)
        self.canvas_timeline_marks.bind("<Button-4>", self._on_canvas_timeline_scroll)  # Linux scroll up
        self.canvas_timeline_marks.bind("<Button-5>", self._on_canvas_timeline_scroll)  # Linux scroll down

        self._atualizar_estado_controles()

    def ativar_modo_livre(self):
        self.modo_livre = True
        self.frame_inputs.configure(text=f"Parâmetros - {self.locacao_nome} (Modo Livre)")

        # No modo livre, o ponto a proteger é derivado automaticamente do CSV.
        try:
            self.entry_ponto_a_proteger.configure(state="disabled")
        except Exception:
            pass

        preview_frame = ttk.LabelFrame(self.frame_inputs, text="Desenvolvimento Livre")
        preview_frame.grid(row=999, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        preview_frame.columnconfigure(1, weight=1)

        ttk.Label(preview_frame, text="Progressiva Final (auto):").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(preview_frame, textvariable=self.var_progressiva_final_livre, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=6, pady=4)

        frame_vma = ttk.LabelFrame(preview_frame, text="VMAs por Faixa")
        frame_vma.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 4))
        ttk.Label(frame_vma, text="Inicio").grid(row=0, column=0, padx=4, pady=2)
        ttk.Label(frame_vma, text="Fim").grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(frame_vma, text="VMA km/h").grid(row=0, column=2, padx=4, pady=2)
        self.entry_vma_inicio = ttk.Entry(frame_vma, width=10)
        self.entry_vma_inicio.grid(row=1, column=0, padx=4, pady=2)
        self.entry_vma_fim = ttk.Entry(frame_vma, width=10)
        self.entry_vma_fim.grid(row=1, column=1, padx=4, pady=2)
        self.entry_vma_valor = ttk.Entry(frame_vma, width=10)
        self.entry_vma_valor.grid(row=1, column=2, padx=4, pady=2)
        ttk.Button(frame_vma, text="Adicionar VMA", command=self._adicionar_vma_livre).grid(row=1, column=3, padx=4, pady=2)
        ttk.Button(frame_vma, text="Remover Ultima", command=self._remover_vma_livre).grid(row=1, column=4, padx=4, pady=2)
        self.var_vma_resumo = tk.StringVar(value="Sem faixas cadastradas")
        ttk.Label(frame_vma, textvariable=self.var_vma_resumo, foreground="#334155").grid(row=2, column=0, columnspan=5, sticky="w", padx=4, pady=(2, 4))

        frame_pausa = ttk.LabelFrame(preview_frame, text="Pausas por Progressiva")
        frame_pausa.grid(row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 4))
        ttk.Label(frame_pausa, text="Progressiva").grid(row=0, column=0, padx=4, pady=2)
        ttk.Label(frame_pausa, text="Duracao s").grid(row=0, column=1, padx=4, pady=2)
        self.entry_pausa_progressiva = ttk.Entry(frame_pausa, width=12)
        self.entry_pausa_progressiva.grid(row=1, column=0, padx=4, pady=2)
        self.entry_pausa_duracao = ttk.Entry(frame_pausa, width=10)
        self.entry_pausa_duracao.grid(row=1, column=1, padx=4, pady=2)
        ttk.Button(frame_pausa, text="Adicionar Pausa", command=self._adicionar_pausa_livre).grid(row=1, column=2, padx=4, pady=2)
        ttk.Button(frame_pausa, text="Remover Ultima", command=self._remover_pausa_livre).grid(row=1, column=3, padx=4, pady=2)
        self.var_pausa_resumo = tk.StringVar(value="Sem pausas cadastradas")
        ttk.Label(frame_pausa, textvariable=self.var_pausa_resumo, foreground="#334155").grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(2, 4))

        self.entry_progressiva.bind("<KeyRelease>", lambda _e: self._atualizar_progressiva_final_livre())
        self.check_var.trace_add("write", lambda *_args: self._atualizar_progressiva_final_livre())
        self._atualizar_progressiva_final_livre()
        self._atualizar_resumo_regras_livre()

    def _atualizar_progressiva_final_livre(self):
        if not self.modo_livre:
            return

        csv_path = self.csv_fullpath or self.entry_csv.get().strip()
        if not csv_path:
            self.var_progressiva_final_livre.set("-")
            return

        try:
            progressiva_inicial = float(self.entry_progressiva.get())
            progressiva_final = grade.calcula_progressiva_final_livre(
                csv_path,
                progressiva_inicial,
                self.check_var.get(),
            )
            self.var_progressiva_final_livre.set(f"{progressiva_final:.2f} m")
            self.entry_ponto_a_proteger.configure(state="normal")
            self.entry_ponto_a_proteger.delete(0, tk.END)
            self.entry_ponto_a_proteger.insert(0, f"{progressiva_final:.2f}")
            self.entry_ponto_a_proteger.configure(state="disabled")
        except Exception:
            self.var_progressiva_final_livre.set("arquivo inválido")

    def _atualizar_resumo_regras_livre(self):
        if not self.modo_livre:
            return
        if self.vmas_livre:
            txt_vma = " | ".join([
                f"[{min(v['inicio'], v['fim']):.0f}-{max(v['inicio'], v['fim']):.0f}]={v['vma_kmh']:.1f}"
                for v in self.vmas_livre
            ])
            self.var_vma_resumo.set(txt_vma)
        else:
            self.var_vma_resumo.set("Sem faixas cadastradas")

        if self.pausas_livre:
            txt_pausa = " | ".join([
                f"P={p['progressiva']:.1f}m, T={p['duracao_s']:.1f}s"
                for p in self.pausas_livre
            ])
            self.var_pausa_resumo.set(txt_pausa)
        else:
            self.var_pausa_resumo.set("Sem pausas cadastradas")

    def _adicionar_vma_livre(self):
        try:
            inicio = float(self.entry_vma_inicio.get())
            fim = float(self.entry_vma_fim.get())
            vma_kmh = float(self.entry_vma_valor.get())
            if vma_kmh <= 0:
                raise ValueError("VMA deve ser positiva.")
            self.vmas_livre.append({"inicio": inicio, "fim": fim, "vma_kmh": vma_kmh})
            self.entry_vma_inicio.delete(0, tk.END)
            self.entry_vma_fim.delete(0, tk.END)
            self.entry_vma_valor.delete(0, tk.END)
            self._atualizar_resumo_regras_livre()
        except Exception as exc:
            messagebox.showerror("Modo Livre", f"Nao foi possivel adicionar VMA: {exc}")

    def _remover_vma_livre(self):
        if self.vmas_livre:
            self.vmas_livre.pop()
            self._atualizar_resumo_regras_livre()

    def _adicionar_pausa_livre(self):
        try:
            progressiva = float(self.entry_pausa_progressiva.get())
            duracao_s = float(self.entry_pausa_duracao.get())
            if duracao_s <= 0:
                raise ValueError("Duracao da pausa deve ser positiva.")
            self.pausas_livre.append({"progressiva": progressiva, "duracao_s": duracao_s})
            self.entry_pausa_progressiva.delete(0, tk.END)
            self.entry_pausa_duracao.delete(0, tk.END)
            self._atualizar_resumo_regras_livre()
        except Exception as exc:
            messagebox.showerror("Modo Livre", f"Nao foi possivel adicionar pausa: {exc}")

    def _remover_pausa_livre(self):
        if self.pausas_livre:
            self.pausas_livre.pop()
            self._atualizar_resumo_regras_livre()

    def _coletar_regras_livre(self, progressiva_inicial, progressiva_final):
        if not self.modo_livre:
            return {}

        pmin = min(float(progressiva_inicial), float(progressiva_final))
        pmax = max(float(progressiva_inicial), float(progressiva_final))

        vmas = []
        for faixa in self.vmas_livre:
            a = min(float(faixa["inicio"]), float(faixa["fim"]))
            b = max(float(faixa["inicio"]), float(faixa["fim"]))
            if a < pmin or b > pmax:
                raise ValueError(f"Faixa VMA [{a:.2f}, {b:.2f}] fora do trecho [{pmin:.2f}, {pmax:.2f}].")
            vmas.append({"inicio": a, "fim": b, "vma_kmh": float(faixa["vma_kmh"])})

        vmas.sort(key=lambda x: (x["inicio"], x["fim"]))
        for i in range(1, len(vmas)):
            if vmas[i]["inicio"] < vmas[i - 1]["fim"]:
                raise ValueError("Faixas de VMA sobrepostas. Ajuste os intervalos.")

        pausas = []
        for pausa in self.pausas_livre:
            p = float(pausa["progressiva"])
            d = float(pausa["duracao_s"])
            if d <= 0:
                raise ValueError("Duracao de pausa deve ser positiva.")
            if p < pmin or p > pmax:
                raise ValueError(f"Pausa em {p:.2f} fora do trecho [{pmin:.2f}, {pmax:.2f}].")
            pausas.append({"progressiva": p, "duracao_s": d})

        return {"vmas": vmas, "pausas": pausas}

    def _cria_entry_label(self, parent, label_text, row, default=""):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=(6, 0))
        entry = ttk.Entry(parent, width=20)
        entry.insert(0, str(default))
        entry.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=(6, 0))
        return entry
    
    def _cria_botao(self, parent, label_text, command, row):
        btn = tk.Button(parent, text=label_text, command=command, bd=2)
        btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        return btn

    def _definir_velocidade_replay(self, fator):
        self._velocidade_selecionada = float(fator)
        if getattr(self, "controlador", None):
            self.controlador.set_velocidade(self._velocidade_selecionada)
        self._atualizar_destaque_velocidade()
        self._atualizar_info_tempo_real()

    def _garantir_animacao_inicializada(self):
        """Inicializa visualizador/controlador uma única vez por locação."""
        if self._animacao_inicializada and getattr(self, "visualizador", None) and getattr(self, "controlador", None):
            return

        self.canvas_animacao.update_idletasks()
        self.visualizador = VisualizadorPatio(main_canvas=self.canvas_animacao, simulador=SimuladorPatio())
        self.controlador = ControladorSimulacao(
            visualizador=self.visualizador,
            root=self.frame.winfo_toplevel(),
            on_finish=None,
        )
        self._animacao_inicializada = True

    def _play_replay(self):
        if getattr(self, "controlador", None):
            self.controlador.play()
        self._atualizar_estado_controles()
        self._atualizar_info_tempo_real()

    def _pause_replay(self):
        if getattr(self, "controlador", None):
            self.controlador.pause()
        self._atualizar_estado_controles()
        self._atualizar_info_tempo_real()

    def _reset_replay(self):
        if getattr(self, "controlador", None):
            self.controlador.stop_reset()
        self.var_alerta_anim.set("")
        self._velocidade_selecionada = 1.0
        self._atualizar_destaque_velocidade()
        self._atualizar_estado_controles()
        self._atualizar_info_tempo_real()
        self._atualizar_timeline(0)

    def _on_timeline_change(self, valor):
        if self._timeline_syncing:
            return
        controlador = getattr(self, "controlador", None)
        if not controlador or not getattr(controlador, "frames", None):
            return

        idx = int(float(valor))
        controlador.ir_para_frame(idx)
        frame_atual = controlador.frames[idx]
        self._atualizar_info_tempo_real(frame_atual)
        self._atualizar_estado_controles()
        self._mover_playhead_timeline(idx)

    def _tempo_para_x_timeline(self, tempo_s):
        x0 = float(self._timeline_meta.get("x0", 92))
        x1 = float(self._timeline_meta.get("x1", 300))
        tempo_final = max(0.0, float(self._timeline_meta.get("tempo_final", 0.0)))
        if tempo_final <= 0.0:
            return x0
        frac = max(0.0, min(1.0, float(tempo_s) / tempo_final))
        return x0 + (x1 - x0) * frac

    def _mover_playhead_timeline(self, idx):
        controlador = getattr(self, "controlador", None)
        if not controlador or not getattr(controlador, "frames", None):
            return
        idx = max(0, min(int(idx), len(controlador.frames) - 1))
        tempo = float(controlador.frames[idx].get("tempo_s", 0.0))
        x = self._tempo_para_x_timeline(tempo)
        y1 = 4
        y2 = max(8, int(self.canvas_timeline_marks.winfo_height()) - 4)

        if self._timeline_playhead_id is None:
            self._timeline_playhead_id = self.canvas_timeline_marks.create_line(
                x,
                y1,
                x,
                y2,
                fill="#dc2626",
                width=2,
            )
        else:
            self.canvas_timeline_marks.coords(self._timeline_playhead_id, x, y1, x, y2)
            self.canvas_timeline_marks.tag_raise(self._timeline_playhead_id)

    def _on_canvas_timeline_scroll(self, event):
        """Lidar com scroll do mouse no canvas_timeline_marks"""
        # Verificar se o canvas tem conteúdo larger than viewport
        bbox = self.canvas_timeline_marks.bbox("all")
        if not bbox:
            return
        
        altura_conteudo = bbox[3] - bbox[1]
        altura_viewport = int(self.canvas_timeline_marks.winfo_height())
        
        # Se o conteúdo cabe na viewport, não faz scroll
        if altura_conteudo <= altura_viewport:
            return
        
        # Calcular quantidade para scroll (5 pixels por scroll event)
        delta = 5
        if event.num == 5 or event.delta < 0:  # scroll down
            delta = -delta
        
        # Deslocar o canvas
        self.canvas_timeline_marks.yview_scroll(delta, "units")

    def _atualizar_timeline(self, idx):
        controlador = getattr(self, "controlador", None)
        if not controlador or not getattr(controlador, "frames", None):
            return
        idx = max(0, min(int(idx), len(controlador.frames) - 1))
        self._timeline_syncing = True
        self.var_timeline.set(float(idx))
        self._timeline_syncing = False
        self._mover_playhead_timeline(idx)

    def _desenhar_marcadores_timeline(self, frames, trens_cfg=None):
        self.canvas_timeline_marks.delete("all")
        self._timeline_playhead_id = None
        if not frames:
            return

        # Forçar cálculo das dimensões do layout antes de desenhar
        # Isso garante que o canvas tenha sua largura correta mesmo se a aba ainda não foi visualizada
        self.frame_timeline.update_idletasks()
        self.canvas_timeline_marks.update_idletasks()
        
        largura = int(self.canvas_timeline_marks.winfo_width())
        if largura <= 10:  # Se ainda não foi renderizado, usar valor padrão
            largura = 820
        largura = max(260, largura)
        x0 = 92
        x1 = largura - 12
        tempo_final = float(frames[-1].get("tempo_s", 0.0)) if frames else 0.0
        self._timeline_meta = {"x0": x0, "x1": x1, "tempo_final": tempo_final}

        cor_por_trem = {}
        if trens_cfg:
            for cfg in trens_cfg:
                tid = str(cfg.get("id", ""))
                if tid:
                    cor_por_trem[tid] = cfg.get("cor", "#1d4ed8")

        tempo_final = float(frames[-1].get("tempo_s", 0.0)) if frames else 0.0
        eventos_trens = frames[-1].get("eventos_trens", {}) if frames else {}
        trem_ids = sorted(str(tid) for tid in eventos_trens.keys())
        if not trem_ids:
            trem_ids = sorted({str(t.get("id", "")) for f in frames for t in f.get("trens", []) if str(t.get("id", ""))})

        trilhas = max(1, len(trem_ids))
        altura = max(30, 10 + trilhas * 18)
        
        # Limitar altura máxima e aplicar scrollbar se necessário
        if altura > self.max_altura_timeline:
            self.canvas_timeline_marks.configure(height=self.max_altura_timeline)
        else:
            self.canvas_timeline_marks.configure(height=altura)

        eventos_ordem = ("t0", "t1", "t2", "t3", "t4", "t5")
        self._timeline_eventos_por_trem = {}
        for idx_trem, trem_id in enumerate(trem_ids):
            y = 14 + idx_trem * 18
            cor_trem = cor_por_trem.get(trem_id, "#1d4ed8")
            self.canvas_timeline_marks.create_text(6, y, text=trem_id, anchor="w", fill=cor_trem, font=("Arial", 8, "bold"))
            self.canvas_timeline_marks.create_line(x0, y, x1, y, fill="#cbd5e1", width=1)

            eventos = eventos_trens.get(trem_id, {})
            if not isinstance(eventos, dict):
                continue
            self._timeline_eventos_por_trem[trem_id] = {}

            for nome in eventos_ordem:
                tempo_evt = eventos.get(nome)
                if tempo_evt is None:
                    continue
                try:
                    tempo_evt = float(tempo_evt)
                except Exception:
                    continue
                x = self._tempo_para_x_timeline(tempo_evt)
                self.canvas_timeline_marks.create_line(x, y - 7, x, y + 7, fill=cor_trem, width=2)
                self.canvas_timeline_marks.create_text(x, y - 10, text=nome, fill="#1e293b", font=("Arial", 7))
                self._timeline_eventos_por_trem[trem_id][nome] = tempo_evt

        # Atualizar a região de scroll do canvas para conteúdo completo
        self.canvas_timeline_marks.configure(scrollregion=self.canvas_timeline_marks.bbox("all"))
        
        self._mover_playhead_timeline(0)

    def _atualizar_estado_controles(self):
        estado = "idle"
        if getattr(self, "controlador", None):
            estado = str(self.controlador.estado)

        if estado == "running":
            self.btn_play.config(state="disabled")
            self.btn_pause.config(state="active")
            self.btn_reset.config(state="active")
        elif estado == "paused":
            self.btn_play.config(state="active")
            self.btn_pause.config(state="disabled")
            self.btn_reset.config(state="active")
        elif estado == "idle":
            # Play habilitado apenas quando ha replay carregado.
            if getattr(self, "controlador", None) and getattr(self.controlador, "frames", None):
                self.btn_play.config(state="active")
            else:
                self.btn_play.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.btn_reset.config(state="disabled")
        else:
            # stopped
            self.btn_play.config(state="active")
            self.btn_pause.config(state="disabled")
            self.btn_reset.config(state="disabled")

    def _atualizar_destaque_velocidade(self):
        # Destaque textual robusto para qualquer tema ttk.
        selecionada = float(self._velocidade_selecionada)
        self.btn_vel_05.configure(text="[0.5x]" if selecionada == 0.5 else "0.5x", bg="#bbbcf1" if selecionada == 0.5 else "#f0f0f0")
        self.btn_vel_10.configure(text="[1.0x]" if selecionada == 1.0 else "1.0x", bg="#bbbcf1" if selecionada == 1.0 else "#f0f0f0")
        self.btn_vel_20.configure(text="[2.0x]" if selecionada == 2.0 else "2.0x", bg="#bbbcf1" if selecionada == 2.0 else "#f0f0f0")

    def _atualizar_info_tempo_real(self, frame_atual=None):
        controlador = getattr(self, "controlador", None)
        if not controlador or not getattr(controlador, "frames", None):
            self.var_info_realtime.set(
                f"Vel: {self._velocidade_selecionada:.1f}x | Tempo: 0.0s | Progresso: 0.0% | Trem: -"
            )
            return

        if frame_atual is None:
            idx = max(0, controlador.frame_atual - 1)
            idx = min(idx, len(controlador.frames) - 1)
            frame_atual = controlador.frames[idx]
        else:
            idx = max(0, min(len(controlador.frames) - 1, controlador.frame_atual - 1))

        tempo = float(frame_atual.get("tempo_s", 0.0))
        progresso = ((idx + 1) / len(controlador.frames)) * 100.0 if controlador.frames else 0.0

        trens_frame = frame_atual.get("trens", [])
        trem_destaque = "-"
        if trens_frame:
            trem_escolhido = max(trens_frame, key=lambda t: float(t.get("progressiva_m", 0.0)))
            trem_destaque = str(trem_escolhido.get("id", "-"))

        self.var_info_realtime.set(
            f"Vel: {self._velocidade_selecionada:.1f}x | Tempo: {tempo:.1f}s | Progresso: {progresso:.1f}% | Trem: {trem_destaque}"
        )

    def _estimar_tempo_saida_s(self, corrida_linhas, tamanho_trem, params=None):
        """Estimativa de T_saida para liberar cauda apos autorizacao.

        Prioriza grades `posfinal` do CSV para estimar aceleracao de partida apos o sinal final.
        Se nao houver dados suficientes, cai para o metodo legado por velocidade media.
        """
        params = params or {}

        # Metodo principal (Fase 5B): usar grades posfinal.
        try:
            csv_path = params.get("csv_path")
            crescente = bool(params.get("crescente", True))
            taxa_frenagem = float(params.get("taxa_frenagem", -0.04))

            if csv_path:
                grades_csv = grade.leGradeCsv(csv_path, crescente)
                posfinal = [g for g in grades_csv if str(g.get("posicao", "")).lower() == "posfinal"]

                if posfinal:
                    distancia_alvo_m = max(1.0, float(tamanho_trem))
                    distancia_acumulada = 0.0
                    integral_grade = 0.0

                    for seg in posfinal:
                        intervalo = max(0.0, float(seg.get("intervalo_grade", 0.0)))
                        if intervalo <= 0:
                            continue

                        restante = max(0.0, distancia_alvo_m - distancia_acumulada)
                        if restante <= 0:
                            break

                        delta = min(intervalo, restante)
                        integral_grade += float(seg.get("grade", 0.0)) * delta
                        distancia_acumulada += delta

                    if distancia_acumulada > 0:
                        grade_media = integral_grade / distancia_acumulada

                        # Aceleracao de partida: base positiva + influencia da grade local.
                        acel_base_partida = max(0.05, abs(taxa_frenagem))
                        termo_grade = -grade_media / 10.0
                        acel_efetiva = max(0.03, acel_base_partida + termo_grade)

                        # Movimento uniformemente acelerado a partir do repouso: s = 0.5*a*t^2.
                        tempo_saida = (2.0 * distancia_alvo_m / acel_efetiva) ** 0.5
                        return max(0.0, float(tempo_saida))
        except Exception:
            # Fallback para manter robustez operacional.
            pass

        # Metodo legado de fallback.
        if not corrida_linhas:
            return 0.0

        velocidades_ms = []
        for row in corrida_linhas:
            v_kmh = float(row.get("Velocidade_kmh", 0.0))
            if v_kmh > 0.0:
                velocidades_ms.append(v_kmh / 3.6)

        if not velocidades_ms:
            return 0.0

        v_ref = max(0.1, float(np.mean(velocidades_ms)))
        return max(0.0, float(tamanho_trem) / v_ref)

    def _estimar_aceleracao_saida_mps2(self, params=None):
        """Estima aceleracao positiva para fase de saida apos parada usando grades posfinal."""
        params = params or {}
        try:
            csv_path = params.get("csv_path")
            crescente = bool(params.get("crescente", True))
            taxa_frenagem = float(params.get("taxa_frenagem", -0.04))
            acel_base_partida = max(0.05, abs(taxa_frenagem))

            if csv_path:
                grades_csv = grade.leGradeCsv(csv_path, crescente)
                posfinal = [g for g in grades_csv if str(g.get("posicao", "")).lower() == "posfinal"]
                if posfinal:
                    dist = sum(max(0.0, float(g.get("intervalo_grade", 0.0))) for g in posfinal)
                    if dist > 0:
                        integral = sum(float(g.get("grade", 0.0)) * max(0.0, float(g.get("intervalo_grade", 0.0))) for g in posfinal)
                        grade_media = integral / dist
                        termo_grade = -grade_media / 10.0
                        return max(0.03, acel_base_partida + termo_grade)

            return acel_base_partida
        except Exception:
            return 0.05

    def _calcular_distancia_saida_alvo_m(self, prog_parada, locacoes, tamanho_trem, crescente):
        """Distancia minima para a cauda desocupar completamente a locacao atual."""
        if not locacoes:
            return max(1.0, float(tamanho_trem))

        p = float(prog_parada)
        tamanho = max(1.0, float(tamanho_trem))
        candidatos = []
        for loc in locacoes:
            p0 = float(loc.get("prog_inicio", p))
            p1 = float(loc.get("prog_fim", p))
            if p1 < p0:
                p0, p1 = p1, p0
            candidatos.append((p0, p1))

        if not candidatos:
            return tamanho

        # Aqui `prog_parada` representa a FRENTE no instante da parada.
        # Para liberar por inteiro, a cauda deve cruzar o limite da locacao.
        if crescente:
            limite = max(p1 for (_, p1) in candidatos)
            desloc = max(0.0, (limite + tamanho + 0.01) - p)
        else:
            limite = min(p0 for (p0, _) in candidatos)
            desloc = max(0.0, p - (limite - tamanho - 0.01))

        return max(1.0, desloc)

    def _construir_trens_cfg_multi(self, quantidade_trens, ciclo_headway_s, passo_de_tempo_s):
        paleta = ["#60a5fa", "#34d399", "#f59e0b", "#f472b6", "#a78bfa", "#22d3ee", "#f87171", "#84cc16"]
        qtd = max(1, int(quantidade_trens))

        v0_base = float(self.entry_velocidade_inicial.get())
        t_freio_base = float(self.entry_tempo_freio_minimo.get())
        tamanho_base = float(self.entry_tamanho_trem.get())
        vma_saida_base = float(self.entry_vma_saida.get())

        trens_cfg = []
        for idx in range(qtd):
            trens_cfg.append({
                "id": f"T{idx + 1:02d}",
                "cor": paleta[idx % len(paleta)],
                "offset_frames": 0,
                "tamanho_trem_m": tamanho_base,
                "vma_saida_kmh": vma_saida_base,
                "velocidade_inicial_kmh": v0_base,
                "tempo_freio_s": t_freio_base,
            })
        return trens_cfg

    def _abrir_editor_trens_pre_execucao(self, trens_cfg):
        top = tk.Toplevel(self.frame)
        top.title(f"Configuração de Trens - {self.locacao_nome}")
        top.transient(self.frame.winfo_toplevel())
        top.grab_set()

        colunas = ("ID", "Tamanho (m)", "VMA Saída (km/h)", "Velocidade Inicial (km/h)", "Tempo de Freio (s)")
        for cidx, titulo in enumerate(colunas):
            ttk.Label(top, text=titulo, font=("Arial", 9, "bold")).grid(row=0, column=cidx, padx=6, pady=6, sticky="w")

        entradas = []
        for ridx, cfg in enumerate(trens_cfg, start=1):
            ttk.Label(top, text=str(cfg.get("id", "-"))).grid(row=ridx, column=0, padx=6, pady=4, sticky="w")

            e_tam = ttk.Entry(top, width=14)
            e_tam.insert(0, f"{float(cfg.get('tamanho_trem_m', 0.0)):.2f}")
            e_tam.grid(row=ridx, column=1, padx=6, pady=4)

            e_vma = ttk.Entry(top, width=14)
            e_vma.insert(0, f"{float(cfg.get('vma_saida_kmh', 0.0)):.2f}")
            e_vma.grid(row=ridx, column=2, padx=6, pady=4)

            e_v0 = ttk.Entry(top, width=14)
            e_v0.insert(0, f"{float(cfg.get('velocidade_inicial_kmh', 0.0)):.2f}")
            e_v0.grid(row=ridx, column=3, padx=6, pady=4)

            e_tf = ttk.Entry(top, width=14)
            e_tf.insert(0, f"{float(cfg.get('tempo_freio_s', 0.0)):.2f}")
            e_tf.grid(row=ridx, column=4, padx=6, pady=4)

            entradas.append((cfg, e_tam, e_vma, e_v0, e_tf))

        resultado = {"confirmado": False, "trens_cfg": trens_cfg}

        def _confirmar():
            try:
                novos_cfg = []
                for cfg_original, e_tam, e_vma, e_v0, e_tf in entradas:
                    tam = float(e_tam.get())
                    vma = float(e_vma.get())
                    v0 = float(e_v0.get())
                    tf = float(e_tf.get())

                    if tam <= 0:
                        raise ValueError("Tamanho do trem deve ser positivo.")
                    if vma <= 0:
                        raise ValueError("VMA de saída deve ser positiva.")
                    if v0 < 0:
                        raise ValueError("Velocidade inicial não pode ser negativa.")
                    if tf <= 0:
                        raise ValueError("Tempo de freio deve ser positivo.")

                    novo = dict(cfg_original)
                    novo["tamanho_trem_m"] = tam
                    novo["vma_saida_kmh"] = vma
                    novo["velocidade_inicial_kmh"] = v0
                    novo["tempo_freio_s"] = tf
                    novos_cfg.append(novo)

                resultado["confirmado"] = True
                resultado["trens_cfg"] = novos_cfg
                top.destroy()
            except Exception as exc:
                messagebox.showerror("Configuração de Trens", str(exc), parent=top)

        def _cancelar():
            top.destroy()

        frame_botoes = ttk.Frame(top)
        frame_botoes.grid(row=len(trens_cfg) + 1, column=0, columnspan=5, sticky="e", padx=8, pady=8)
        ttk.Button(frame_botoes, text="Cancelar", command=_cancelar).pack(side="right", padx=6)
        ttk.Button(frame_botoes, text="Confirmar", command=_confirmar).pack(side="right", padx=6)

        # Centraliza a janela de configuracao em relacao a janela principal.
        top.update_idletasks()
        parent = self.frame.winfo_toplevel()
        parent.update_idletasks()
        largura = top.winfo_width()
        altura = top.winfo_height()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - largura) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - altura) // 2)
        top.geometry(f"+{x}+{y}")

        top.wait_window()
        return resultado["confirmado"], resultado["trens_cfg"]
    
    def on_button_click(self):
        try:
            self._run_token += 1
            run_token = self._run_token

            # Encerra callbacks de replay anterior antes de recriar estruturas.
            if self._after_telemetria:
                self.frame.after_cancel(self._after_telemetria)
                self._after_telemetria = None
            if self._after_alerta:
                self.frame.after_cancel(self._after_alerta)
                self._after_alerta = None
            if getattr(self, "controlador", None) and getattr(self.controlador, "after_id", None):
                self.controlador.root.after_cancel(self.controlador.after_id)
                self.controlador.after_id = None

            params = {
                "csv_path": self.csv_fullpath or self.entry_csv.get(),
                "progressiva": float(self.entry_progressiva.get()),
                "nome_sinal_a": self.entry_nome_sinal_a.get().strip(),
                "ponto_a_proteger": float(self.entry_ponto_a_proteger.get()),
                "nome_sinal_b": self.entry_nome_sinal_b.get().strip(),
                "crescente": self.check_var.get(),
                "velocidade_inicial_kmh": float(self.entry_velocidade_inicial.get()),
                "passo_de_tempo_s": 0.5,
                "tempo_freio_minimo_s": float(self.entry_tempo_freio_minimo.get()),
                "tempo_equalizacao_freio_s": float(self.entry_tempo_equalizacao.get()),
                "tempo_parado_s": float(self.entry_tempo_parado.get()),
                "quantidade_trens": int(float(self.entry_qtd_trens.get())),
                "taxa_frenagem": float(self.entry_taxa_frenagem.get()),
                "tamanho_trem": float(self.entry_tamanho_trem.get()),
                "vma_saida_kmh": float(self.entry_vma_saida.get()),
                "step": float(self.entry_step.get()),
            }

            if self.modo_livre:
                params["ponto_a_proteger"] = grade.calcula_progressiva_final_livre(
                    params["csv_path"],
                    params["progressiva"],
                    params["crescente"],
                )
                regras_livre = self._coletar_regras_livre(
                    params["progressiva"],
                    params["ponto_a_proteger"],
                )
                self.entry_ponto_a_proteger.configure(state="normal")
                self.entry_ponto_a_proteger.delete(0, tk.END)
                self.entry_ponto_a_proteger.insert(0, f"{params['ponto_a_proteger']:.2f}")
                self.entry_ponto_a_proteger.configure(state="disabled")
                self.var_progressiva_final_livre.set(f"{params['ponto_a_proteger']:.2f} m")
            else:
                regras_livre = None
                
            self.verifica_dados(params)
            self.last_params = params
            
            params_pipeline = dict(params)
            params_pipeline.pop("tempo_parado_s", None)
            params_pipeline.pop("quantidade_trens", None)
            params_pipeline.pop("vma_saida_kmh", None)
            params_pipeline.pop("nome_sinal_a", None)
            params_pipeline.pop("nome_sinal_b", None)
            if self.modo_livre:
                params_pipeline.pop("ponto_a_proteger", None)
                params_pipeline["regras_operacionais"] = regras_livre
                results = pipeline.run_pipeline_livre(**params_pipeline)
            else:
                results = pipeline.run_pipeline(**params_pipeline)
            
            corrida = results.get("corrida", [])
 
            if corrida:
                prog_ini = float(min(r["Progressiva_m"] for r in corrida))
                prog_fim = float(max(r["Progressiva_m"] for r in corrida))
            else:
                prog_ini, prog_fim = 0.0, 1.0
            
            sinais = self._construir_sinais_por_grade(params, prog_ini, prog_fim)
            locacoes = self._construir_locacoes_por_grade(
                params,
                sinais,
                prog_ini,
                prog_fim,
            )

            tempo_total_corrida_s = float(corrida[-1].get("Tempo_s", 0.0)) if corrida else 0.0
            aceleracao_saida_mps2 = self._estimar_aceleracao_saida_mps2(params=params)
            prog_parada = float(corrida[-1].get("Progressiva_m", params["progressiva"])) if corrida else float(params["progressiva"])
            distancia_saida_alvo_m = self._calcular_distancia_saida_alvo_m(
                prog_parada,
                locacoes,
                params["tamanho_trem"],
                params["crescente"],
            )

            tempo_saida_estimado_s = (2.0 * max(1.0, float(distancia_saida_alvo_m)) / max(0.03, float(aceleracao_saida_mps2))) ** 0.5
            ciclo_headway_s = tempo_total_corrida_s + float(params["tempo_parado_s"]) + tempo_saida_estimado_s
            trens_cfg = self._construir_trens_cfg_multi(
                quantidade_trens=params["quantidade_trens"],
                ciclo_headway_s=ciclo_headway_s,
                passo_de_tempo_s=params["passo_de_tempo_s"],
            )

            confirmado, trens_cfg_editado = self._abrir_editor_trens_pre_execucao(trens_cfg)
            if not confirmado:
                return
            trens_cfg = trens_cfg_editado

            frames = self.corrida_para_frames_despacho_evento(
                corrida, 
                trens_cfg, 
                locacoes, 
                sinais,
                tamanho_trem=params["tamanho_trem"],
                crescente=params["crescente"],
                passo_de_tempo_s=params["passo_de_tempo_s"],
                tempo_parado_s=params["tempo_parado_s"],
                aceleracao_saida_mps2=aceleracao_saida_mps2,
                distancia_saida_alvo_m=distancia_saida_alvo_m,
            )

            # Garante que a janela visual da rota inclui sinais e toda a extensao de movimento dos frames.
            # Sem isso, o trem pode parecer "travado" no mesmo ponto por clamp de eixo no renderer.
            posicoes_referencia = [prog_ini, prog_fim]
            if sinais:
                posicoes_referencia.extend(float(s.get("posicao", 0.0)) for s in sinais)

            if frames:
                for f in frames:
                    for t in f.get("trens", []):
                        posicoes_referencia.append(float(t.get("progressiva_m", 0.0)))

            if posicoes_referencia:
                prog_ini = min(posicoes_referencia)
                prog_fim = max(posicoes_referencia)

            self._garantir_animacao_inicializada()
            self.canvas_animacao.delete("trem")
            self.canvas_animacao.delete("trem_label")
            self.tabela_telemetria.delete(*self.tabela_telemetria.get_children())
            self.var_alerta_anim.set("")

            if hasattr(self.visualizador, "alerta_id"):
                try:
                    self.canvas_animacao.delete(self.visualizador.alerta_id)
                except Exception:
                    pass
                delattr(self.visualizador, "alerta_id")

            self.visualizador.trens = {}
            self.visualizador.set_contexto_rota(prog_ini, prog_fim, locacoes, sinais)

            self.replay_finalizado = False

            def _on_finish_replay():
                self.replay_finalizado = True
                self._atualizar_estado_controles()

            self.controlador.on_finish = _on_finish_replay
            self.controlador.carregar_replay(frames)
            self.scale_timeline.configure(to=max(0, len(frames) - 1))
            self._atualizar_timeline(0)
            self._desenhar_marcadores_timeline(frames, trens_cfg=trens_cfg)
            self._velocidade_selecionada = 1.0
            self._atualizar_destaque_velocidade()
            self._atualizar_estado_controles()
            self._atualizar_info_tempo_real()

            def _atualiza_telemetria():
                if run_token != self._run_token:
                    return
                if getattr(self, "controlador", None) and self.controlador.frames:
                    idx = max(0, self.controlador.frame_atual - 1)
                    idx = min(idx, len(self.controlador.frames) - 1)
                    frame_atual = self.controlador.frames[idx]

                    self.tabela_telemetria.delete(*self.tabela_telemetria.get_children())
                    for t in frame_atual.get("trens", []):
                        tid = t.get("id", "-")
                        v = float(t.get("velocidade_kmh", 0.0))
                        p = float(t.get("progressiva_m", 0.0))
                        a = float(t.get("aceleracao_mps2", 0.0))
                        status = t.get("status_operacional", "-")

                        self.tabela_telemetria.insert(
                            "",
                            "end",
                            values=(
                                tid,
                                status,
                                f"{v:.2f}",
                                f"{p:.2f}",
                                f"{a:.4f}",
                            ),
                        )
                    self._atualizar_estado_controles()
                    self._atualizar_info_tempo_real(frame_atual)
                    self._atualizar_timeline(idx)
                self._after_telemetria = self.frame.after(120, _atualiza_telemetria)

            _atualiza_telemetria()

            def _atualiza_alerta():
                if run_token != self._run_token:
                    return
                if getattr(self, "controlador", None) and self.controlador.frames:
                    if self.controlador.estado == "running":
                        self.replay_finalizado = False

                    idx = max(0, self.controlador.frame_atual - 1)
                    idx = min(idx, len(self.controlador.frames) - 1)
                    f = self.controlador.frames[idx]
                    if f.get("bloqueados", []):
                        self.var_alerta_anim.set("Aguardando locacao: " + ", ".join(f.get("bloqueados", [])))
                    elif f.get("conflito_ocupacao", False):
                        self.var_alerta_anim.set("Conflito: dois trens na locacao")
                    elif self.replay_finalizado:
                        self.var_alerta_anim.set("Replay concluido")
                    else:
                        self.var_alerta_anim.set("")
                self._after_alerta = self.frame.after(120, _atualiza_alerta)

            _atualiza_alerta()

            primeira_progressiva_por_trem = {}
            if frames:
                for t in frames[0].get("trens", []):
                    tid = str(t.get("id", ""))
                    if tid:
                        primeira_progressiva_por_trem[tid] = float(t.get("progressiva_m", params["progressiva"]))

            for cfg in trens_cfg:
                self.visualizador.registrar_trem(
                    trem_id=cfg["id"],
                    cor=cfg["cor"],
                    comprimento_visual_px=30,
                    comprimento_m=float(cfg.get("tamanho_trem_m", params["tamanho_trem"])),
                    crescente=params["crescente"],
                    progressiva_inicial_m=primeira_progressiva_por_trem.get(cfg["id"], params["progressiva"]),
                )

            self.results = results
            self.results["eventos_trens"] = frames[-1].get("eventos_trens", {}) if frames else {}
            self.results["tempo_saida_estimado_s"] = tempo_saida_estimado_s
            self.results["aceleracao_saida_mps2"] = aceleracao_saida_mps2
            self.results["distancia_saida_alvo_m"] = distancia_saida_alvo_m
            self.results["ciclo_headway_s"] = ciclo_headway_s
            
            crescente = params["crescente"]
            
            self.preenche_tabela_corrida(results["corrida"])
            self.plota_grade(results["serie"], crescente)
            self.plota_corrida(results["corrida"], crescente)
            self.plota_diagrama_espaco_tempo(frames, trens_cfg)
            self.atualiza_resumo(results["corrida"])
            
            # Se o main_app existir, atualiza os dados
            if self.main_app:
                self.main_app.atualiza_dados_relatorio()
        
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao executar a simulação.\nErro: {str(e)}")

    def _construir_sinais_por_grade(self, params, prog_ini_fallback, prog_fim_fallback):
        """Monta sinais usando a regra de negócio:
        - Primeiro sinal: progressiva no ponto 'na', equivalente ao inicio do perfil + tamanho do trem.
        - Último sinal: sempre no ponto a proteger (regra operacional).
        """
        try:
            grades = grade.leGradeCsv(params["csv_path"], params["crescente"])
            if not grades:
                raise ValueError("CSV sem grades")

            grades = grade.insere_primeiro_valor(grades, params["tamanho_trem"])
            grades = grade.anotaFaixasProgressiva(
                grades,
                progressiva_inicial=params["progressiva"],
                crescente=params["crescente"],
                tamanho_trem=params["tamanho_trem"],
            )

            prog_inicios = [float(g.get("prog_inicio")) for g in grades if g.get("prog_inicio") is not None]
            if params["crescente"]:
                inicio_perfil = min(prog_inicios) if prog_inicios else float(params["progressiva"])
                sinal_inicial_calc = inicio_perfil + float(params["tamanho_trem"])
            else:
                inicio_perfil = max(prog_inicios) if prog_inicios else float(params["progressiva"])
                sinal_inicial_calc = inicio_perfil - float(params["tamanho_trem"])

            primeiro_na = next((g for g in grades if g.get("posicao") == "na"), None)
            if primeiro_na is not None:
                sinal_inicial = float(primeiro_na.get("prog_inicio", params["progressiva"]))
            else:
                sinal_inicial = float(sinal_inicial_calc)

            # Mantem alinhamento com o tamanho do trem e evita divergencia numerica acumulada.
            if abs(sinal_inicial - sinal_inicial_calc) > 1e-6:
                sinal_inicial = float(sinal_inicial_calc)

            sinal_final = float(params.get("ponto_a_proteger", prog_fim_fallback))

            nome_sinal_a = str(params.get("nome_sinal_a", "") or "").strip() or f"S_{self.locacao_nome}_A"
            nome_sinal_b = str(params.get("nome_sinal_b", "") or "").strip() or f"S_{self.locacao_nome}_B"

            return [
                {"id": nome_sinal_a, "posicao": sinal_inicial, "estado": "AMARELO"},
                {"id": nome_sinal_b, "posicao": sinal_final, "estado": "VERMELHO"},
            ]
        except Exception:
            nome_sinal_a = str(params.get("nome_sinal_a", "") or "").strip() or f"S_{self.locacao_nome}_A"
            nome_sinal_b = str(params.get("nome_sinal_b", "") or "").strip() or f"S_{self.locacao_nome}_B"
            return [
                {"id": nome_sinal_a, "posicao": float(prog_ini_fallback), "estado": "AMARELO"},
                {"id": nome_sinal_b, "posicao": float(prog_fim_fallback), "estado": "VERMELHO"},
            ]

    def _construir_locacoes_por_grade(self, params, sinais, prog_ini_fallback, prog_fim_fallback):
        """Monta locacoes ativa principal e pos-sinal ativa para visualizacao de ocupacao."""
        try:
            if not sinais or len(sinais) < 2:
                raise ValueError("Sinais insuficientes")

            posicoes = sorted(float(s.get("posicao")) for s in sinais)
            p0 = posicoes[0]
            p1 = posicoes[-1]

            if p1 < p0:
                p0, p1 = p1, p0

            crescente = bool(params.get("crescente", True))
            p_min_fallback = float(min(prog_ini_fallback, prog_fim_fallback))
            p_max_fallback = float(max(prog_ini_fallback, prog_fim_fallback))
            tamanho_trem = max(1.0, float(params.get("tamanho_trem", 1.0)))
            if crescente:
                pos_ini = p1
                pos_fim = max(p_max_fallback, p1 + tamanho_trem)
            else:
                pos_ini = min(p_min_fallback, p0 - tamanho_trem)
                pos_fim = p0

            return [
                {
                    "id": "LOC_01",
                    "label": f"LOC 01 ({p0:.0f}-{p1:.0f} m)",
                    "prog_inicio": float(p0),
                    "prog_fim": float(p1),
                    "passiva": False,
                },
                {
                    "id": "LOC_POS",
                    "label": f"LOC Pós ({pos_ini:.0f}-{pos_fim:.0f} m)",
                    "prog_inicio": float(pos_ini),
                    "prog_fim": float(pos_fim),
                    "passiva": False,
                }, 
            ]
        except Exception:
            pass

        return [
            {
                "id": "LOC_01",
                "label": "LOC 01",
                "prog_inicio": float(prog_ini_fallback),
                "prog_fim": float(prog_fim_fallback),
                "passiva": False,
            },
            {
                "id": "LOC_POS",
                "label": "LOC Pós",
                "prog_inicio": float(
                    max(prog_ini_fallback, prog_fim_fallback)
                    if bool(params.get("crescente", True))
                    else min(prog_ini_fallback, prog_fim_fallback) - max(1.0, float(params.get("tamanho_trem", 1.0)))
                ),
                "prog_fim": float(
                    max(prog_ini_fallback, prog_fim_fallback) + max(1.0, float(params.get("tamanho_trem", 1.0)))
                    if bool(params.get("crescente", True))
                    else min(prog_ini_fallback, prog_fim_fallback)
                ),
                "passiva": False,
            },
        ]

    def _locacoes_da_progressiva(self, progressiva_m, locacoes, tamanho_trem, crescente, incluir_passivas=False):
        """Determina quais locações um trem ocupa, considerando seu comprimento.
        
        O trem ocupa um intervalo [traseira, frente]:
        - Se crescente: [progressiva_m, progressiva_m + tamanho_trem]
        - Se não crescente: [progressiva_m - tamanho_trem, progressiva_m]
        
        Uma locação [p0, p1] é ocupada se houver overlap com o intervalo do trem.
        Overlap existe quando: trem_fim > p0 AND trem_inicio < p1
        """
        p_traseira = float(progressiva_m)
        tamanho = float(tamanho_trem)
        
        # Calcular intervalo que o trem ocupa
        if crescente:
            p_trem_inicio = p_traseira
            p_trem_fim = p_traseira + tamanho
        else:
            p_trem_inicio = p_traseira - tamanho
            p_trem_fim = p_traseira
        
        correspondentes = []
        for loc in locacoes:
            if not incluir_passivas and bool(loc.get("passiva", False)):
                continue
            p0 = float(loc.get("prog_inicio", p_traseira))
            p1 = float(loc.get("prog_fim", p_traseira))
            if p1 < p0:
                p0, p1 = p1, p0
            
            # Verificar overlap entre [p_trem_inicio, p_trem_fim] e [p0, p1]
            # Há overlap se: trem_fim > p0 AND trem_inicio < p1
            tem_overlap = (p_trem_fim > p0) and (p_trem_inicio < p1)
            
            if tem_overlap:
                correspondentes.append(str(loc.get("id")))
        
        return correspondentes

    def corrida_para_frames_multi(self, corrida_linhas, trens_cfg, locacoes, sinais=None, tamanho_trem=None, crescente=None, passo_de_tempo_s=0.5):
        frames = []
        if not corrida_linhas:
            return frames

        sinais = sinais or []
        tamanho_trem = float(0.0 if tamanho_trem is None else tamanho_trem)
        crescente = True if crescente is None else bool(crescente)

        sinal_a_id = str(sinais[0].get("id")) if len(sinais) >= 1 else "S_A"
        sinal_b_id = str(sinais[1].get("id")) if len(sinais) >= 2 else "S_B"

        sinais_por_id = {
            str(sig.get("id", "")): float(sig.get("posicao", 0.0))
            for sig in sinais
        }
        sinal_a_pos = sinais_por_id.get(sinal_a_id)
        sinal_b_pos = sinais_por_id.get(sinal_b_id)

        def _cruzou_referencia(valor_anterior, valor_atual, referencia, sentido_crescente):
            if referencia is None:
                return False
            atual = float(valor_atual)
            if valor_anterior is None:
                return atual >= referencia if sentido_crescente else atual <= referencia
            anterior = float(valor_anterior)
            if sentido_crescente:
                return (anterior < referencia <= atual) or abs(atual - referencia) <= 1e-9
            return (anterior > referencia >= atual) or abs(atual - referencia) <= 1e-9

        total = len(corrida_linhas)
        max_offset_frames = max((int(cfg.get("offset_frames", 0)) for cfg in trens_cfg), default=0)
        total_frames = total + max(0, max_offset_frames)
        estado_trens = {
            cfg["id"]: {
                "prog_anterior": None,
                "tempo_anterior": None,
                "locacao_id": None,
                "frente_anterior": None,
                "cauda_anterior": None,
                "vel_anterior": None,
                "sinal_b_estado_anterior": None,
                "eventos": {
                    "t0": None,
                    "t1": None,
                    "t2": None,
                    "t3": None,
                    "t4": None,
                    "t5": None,
                },
            }
            for cfg in trens_cfg
        }

        for i in range(total_frames):
            if i < total:
                row = corrida_linhas[i]
                tempo = float(row.get("Tempo_s", i * float(passo_de_tempo_s)))
                base_prog = float(row.get("Progressiva_m", 0.0))
                base_vel = float(row.get("Velocidade_kmh", 0.0))
            else:
                row = corrida_linhas[-1]
                tempo = float(i) * float(passo_de_tempo_s)
                base_prog = float(row.get("Progressiva_m", 0.0))
                base_vel = 0.0

            trens = []
            ocupantes = []
            bloqueados = []
            ocupantes_por_locacao = {
                str(loc.get("id")): None
                for loc in locacoes
            }

            for cfg in trens_cfg:
                idx = i - int(cfg.get("offset_frames", 0))
                if idx < 0 or idx >= total:
                    continue

                row_t = corrida_linhas[idx]
                prog_candidato = float(row_t.get("Progressiva_m", base_prog))
                vel_candidato = float(row_t.get("Velocidade_kmh", base_vel))
                acel_candidato = float(row_t.get("Aceleracao_mps2", 0.0))
                trem_id = cfg["id"]
                estado_trem = estado_trens[trem_id]

                tempo_anterior = estado_trem["tempo_anterior"]
                dt = 0.0 if tempo_anterior is None else max(0.0, tempo - tempo_anterior)

                locacoes_candidatas = self._locacoes_da_progressiva(
                    prog_candidato, 
                    locacoes, 
                    tamanho_trem,
                    crescente
                )
                loc_anterior = estado_trens[trem_id].get("locacao_id")
                loc_trem_id = None

                if loc_anterior in locacoes_candidatas and ocupantes_por_locacao.get(loc_anterior) in (None, trem_id):
                    loc_trem_id = loc_anterior
                else:
                    for loc_id in locacoes_candidatas:
                        if ocupantes_por_locacao.get(loc_id) in (None, trem_id):
                            loc_trem_id = loc_id
                            break

                if vel_candidato > 0 and locacoes_candidatas and loc_trem_id is None:
                    prog_anterior = estado_trem["prog_anterior"]
                    prog = prog_anterior if prog_anterior is not None else prog_candidato
                    vel = 0.0
                    acel = 0.0
                    bloqueados.append(trem_id)
                    status_operacional = "AGUARDANDO"
                else:
                    prog = prog_candidato
                    vel = vel_candidato
                    acel = acel_candidato

                    if loc_trem_id is not None:
                        ocupantes_por_locacao[loc_trem_id] = trem_id
                        if trem_id not in ocupantes:
                            ocupantes.append(trem_id)

                    status_operacional = "EM_MOVIMENTO" if vel > 0 else "PARADO"

                # Eventos operacionais por trem (t0..t5).
                eventos = estado_trem["eventos"]
                frente_atual = prog + tamanho_trem if crescente else prog - tamanho_trem
                cauda_atual = prog
                frente_anterior = estado_trem["frente_anterior"]
                cauda_anterior = estado_trem["cauda_anterior"]
                vel_anterior = 0.0 if estado_trem["vel_anterior"] is None else float(estado_trem["vel_anterior"])

                if eventos["t0"] is None and _cruzou_referencia(frente_anterior, frente_atual, sinal_a_pos, crescente):
                    eventos["t0"] = tempo

                if eventos["t4"] is None and _cruzou_referencia(frente_anterior, frente_atual, sinal_b_pos, crescente):
                    eventos["t4"] = tempo

                if eventos["t5"] is None and _cruzou_referencia(cauda_anterior, cauda_atual, sinal_b_pos, crescente):
                    eventos["t5"] = tempo

                # t1 = chegada/parada junto ao sinal final (com tolerancia numerica).
                if eventos["t1"] is None and sinal_b_pos is not None:
                    tolerancia_m = 1.0
                    chegou_ao_sinal_final = (
                        (frente_atual >= (sinal_b_pos - tolerancia_m)) if crescente
                        else (frente_atual <= (sinal_b_pos + tolerancia_m))
                    )
                    if vel <= 0.0 and chegou_ao_sinal_final:
                        eventos["t1"] = tempo

                # t3 = retomada de movimento apos autorizacao (t2).
                if eventos["t3"] is None and eventos["t2"] is not None:
                    if vel_anterior <= 0.0 and vel > 0.0:
                        eventos["t3"] = tempo

                estado_trem["prog_anterior"] = prog
                estado_trem["tempo_anterior"] = tempo
                estado_trem["frente_anterior"] = frente_atual
                estado_trem["cauda_anterior"] = cauda_atual
                estado_trem["vel_anterior"] = vel
                if loc_trem_id is not None:
                    estado_trem["locacao_id"] = loc_trem_id

                trens.append({
                    "id": trem_id,
                    "progressiva_m": prog,
                    "velocidade_kmh": vel,
                    "aceleracao_mps2": acel,
                    "bloqueado": trem_id in bloqueados,
                    "status_operacional": status_operacional,
                    "eventos": dict(eventos),
                })

            ha_ocupacao = any(v is not None for v in ocupantes_por_locacao.values())
            ha_bloqueio = bool(bloqueados)
            if ha_bloqueio:
                estado_sinal_a = "VERMELHO"
                estado_sinal_b = "VERMELHO"
            elif ha_ocupacao:
                estado_sinal_a = "AMARELO"
                estado_sinal_b = "VERMELHO"
            else:
                estado_sinal_a = "AMARELO"
                estado_sinal_b = "AMARELO"

            # t2 = autorizacao quando sinal final deixa de estar vermelho apos a parada.
            for trem in trens:
                trem_id = str(trem.get("id", ""))
                if not trem_id or trem_id not in estado_trens:
                    continue
                estado_trem = estado_trens[trem_id]
                eventos = estado_trem["eventos"]
                sinal_b_anterior = estado_trem.get("sinal_b_estado_anterior")

                if eventos["t1"] is not None and eventos["t2"] is None:
                    if sinal_b_anterior == "VERMELHO" and estado_sinal_b != "VERMELHO":
                        eventos["t2"] = tempo

                estado_trem["sinal_b_estado_anterior"] = estado_sinal_b
                trem["eventos"] = dict(eventos)

            frames.append({
                "tempo_s": tempo,
                "trens": trens,
                "sinais": [
                    {"id": sinal_a_id, "estado": estado_sinal_a},
                    {"id": sinal_b_id, "estado": estado_sinal_b},
                ],
                "locacoes": [
                    {
                        "id": loc_id,
                        "ocupante_trem_id": trem_id,
                    }
                    for loc_id, trem_id in ocupantes_por_locacao.items()
                ],
                "conflito_ocupacao": False,
                "ocupantes": ocupantes,
                "bloqueados": bloqueados,
                "eventos_trens": {
                    trem_id: dict(estado["eventos"])
                    for trem_id, estado in estado_trens.items()
                },
            })

        return frames

    def corrida_para_frames_despacho_evento(
        self,
        corrida_linhas,
        trens_cfg,
        locacoes,
        sinais=None,
        tamanho_trem=None,
        crescente=None,
        passo_de_tempo_s=0.5,
        tempo_parado_s=5.0,
        aceleracao_saida_mps2=0.05,
        distancia_saida_alvo_m=None,
    ):
        """Gera frames com despacho real por bloco: proximo trem so entra apos t5 do anterior."""
        if not corrida_linhas:
            return []

        sinais = sinais or []
        tamanho_trem = float(0.0 if tamanho_trem is None else tamanho_trem)
        crescente = True if crescente is None else bool(crescente)
        dt = max(1e-6, float(passo_de_tempo_s))
        tempo_parado_s = max(0.0, float(tempo_parado_s))
        a_saida = max(0.03, float(aceleracao_saida_mps2))
        dist_saida = max(1.0, float(distancia_saida_alvo_m if distancia_saida_alvo_m is not None else tamanho_trem))

        sinal_a_id = str(sinais[0].get("id")) if len(sinais) >= 1 else "S_A"
        sinal_b_id = str(sinais[1].get("id")) if len(sinais) >= 2 else "S_B"
        sinais_por_id = {str(sig.get("id", "")): float(sig.get("posicao", 0.0)) for sig in sinais}
        sinal_a_pos = sinais_por_id.get(sinal_a_id)
        sinal_b_pos = sinais_por_id.get(sinal_b_id)

        def _cruzou_referencia(valor_anterior, valor_atual, referencia, sentido_crescente):
            if referencia is None:
                return False
            atual = float(valor_atual)
            if valor_anterior is None:
                return atual >= referencia if sentido_crescente else atual <= referencia
            anterior = float(valor_anterior)
            if sentido_crescente:
                return (anterior < referencia <= atual) or abs(atual - referencia) <= 1e-9
            return (anterior > referencia >= atual) or abs(atual - referencia) <= 1e-9

        ordem_trens = [str(cfg.get("id")) for cfg in trens_cfg if str(cfg.get("id", ""))]
        cfg_por_trem = {
            str(cfg.get("id")): dict(cfg)
            for cfg in trens_cfg
            if str(cfg.get("id", ""))
        }
        cor_por_trem = {str(cfg.get("id")): cfg.get("cor", "#60a5fa") for cfg in trens_cfg}
        if not ordem_trens:
            return []

        total_corrida = len(corrida_linhas)
        max_frames = int((total_corrida + 6000) * max(1, len(ordem_trens)))

        estado_trens = {}
        for i, trem_id in enumerate(ordem_trens):
            estado_trens[trem_id] = {
                "fase": "CORRIDA" if i == 0 else "PENDENTE_ENTRADA",
                "idx_corrida": 0,
                "tempo_fase": 0.0,
                "prog_atual": None,
                "vel_atual": 0.0,
                "acel_atual": 0.0,
                "prog_parada": None,
                "frente_anterior": None,
                "cauda_anterior": None,
                "vel_anterior": None,
                "liberado": False,
                "eventos": {"t0": None, "t1": None, "t2": None, "t3": None, "t4": None, "t5": None},
            }

        frames = []
        for frame_idx in range(max_frames):
            tempo = frame_idx * dt

            # Regra de bloco: trem i+1 entra apenas apos t5 real do trem i.
            for i in range(1, len(ordem_trens)):
                trem_prev = ordem_trens[i - 1]
                trem_atual = ordem_trens[i]
                if estado_trens[trem_atual]["fase"] == "PENDENTE_ENTRADA" and estado_trens[trem_prev]["liberado"]:
                    estado_trens[trem_atual]["fase"] = "CORRIDA"
                    estado_trens[trem_atual]["idx_corrida"] = 0
                    estado_trens[trem_atual]["tempo_fase"] = 0.0

            trens_frame = []
            ocupantes_por_locacao = {str(loc.get("id")): None for loc in locacoes}
            bloqueados = []
            ocupantes = []

            for trem_id in ordem_trens:
                st = estado_trens[trem_id]
                fase = st["fase"]

                if fase == "PENDENTE_ENTRADA":
                    continue

                if fase == "CORRIDA":
                    cfg_trem = cfg_por_trem.get(trem_id, {})
                    idx_float = float(st["idx_corrida"])
                    idx = min(int(idx_float), total_corrida - 1)
                    row = corrida_linhas[idx]
                    prog = float(row.get("Progressiva_m", 0.0))
                    vel = float(row.get("Velocidade_kmh", 0.0))
                    acel = float(row.get("Aceleracao_mps2", 0.0))

                    v0_cfg = max(0.0, float(cfg_trem.get("velocidade_inicial_kmh", vel)))
                    vel = min(vel, v0_cfg)

                    t_freio_cfg = max(1e-6, float(cfg_trem.get("tempo_freio_s", tempo_parado_s if tempo_parado_s > 0 else 1.0)))
                    t_freio_ref = max(1e-6, float(getattr(self, "last_params", {}).get("tempo_freio_minimo_s", t_freio_cfg)))
                    fator_freio = max(0.25, t_freio_cfg / t_freio_ref)
                    st["idx_corrida"] += (1.0 / fator_freio)

                    if st["idx_corrida"] >= total_corrida:
                        st["fase"] = "PARADO_AUTORIZACAO"
                        st["tempo_fase"] = 0.0
                        st["prog_parada"] = prog
                        st["eventos"]["t1"] = tempo if st["eventos"]["t1"] is None else st["eventos"]["t1"]

                    status_operacional = "EM_MOVIMENTO" if vel > 0 else "PARADO"

                elif fase == "PARADO_AUTORIZACAO":
                    prog = float(st["prog_parada"] if st["prog_parada"] is not None else corrida_linhas[-1].get("Progressiva_m", 0.0))
                    vel = 0.0
                    acel = 0.0
                    st["tempo_fase"] += dt
                    status_operacional = "AGUARDANDO_AUTORIZACAO"

                    if st["tempo_fase"] >= tempo_parado_s:
                        st["fase"] = "SAIDA"
                        st["tempo_fase"] = 0.0
                        if st["eventos"]["t2"] is None:
                            st["eventos"]["t2"] = tempo
                        if st["eventos"]["t3"] is None:
                            st["eventos"]["t3"] = tempo

                elif fase == "SAIDA":
                    cfg_trem = cfg_por_trem.get(trem_id, {})
                    prog_base = float(st["prog_parada"] if st["prog_parada"] is not None else corrida_linhas[-1].get("Progressiva_m", 0.0))
                    t_saida = st["tempo_fase"]
                    # A saida continua ate a cauda cruzar o sinal final (t5 real),
                    # sem travar por limite estimado de deslocamento.
                    vma_saida_kmh = max(1.0, float(cfg_trem.get("vma_saida_kmh", 60.0)))
                    vma_saida_ms = vma_saida_kmh / 3.6
                    tempo_para_vma = vma_saida_ms / a_saida
                    if t_saida <= tempo_para_vma:
                        desloc = 0.5 * a_saida * (t_saida ** 2)
                        vel_ms = a_saida * t_saida
                    else:
                        desloc = (0.5 * a_saida * (tempo_para_vma ** 2)) + (vma_saida_ms * (t_saida - tempo_para_vma))
                        vel_ms = vma_saida_ms
                    prog = prog_base + desloc if crescente else prog_base - desloc
                    vel = max(0.0, min(vel_ms * 3.6, vma_saida_kmh))
                    acel = a_saida
                    st["tempo_fase"] += dt
                    status_operacional = "EM_SAIDA"

                else:
                    prog = float(st["prog_atual"] if st["prog_atual"] is not None else corrida_linhas[-1].get("Progressiva_m", 0.0))
                    vel = 0.0
                    acel = 0.0
                    status_operacional = "PARADO_LIBERADO"

                # `prog` representa a FRENTE da locomotiva. Para ocupacao, converte para cauda.
                tamanho_trem_t = max(1.0, float(cfg_por_trem.get(trem_id, {}).get("tamanho_trem_m", tamanho_trem)))
                prog_cauda = (prog - tamanho_trem_t) if crescente else (prog + tamanho_trem_t)
                locacoes_candidatas = self._locacoes_da_progressiva(prog_cauda, locacoes, tamanho_trem_t, crescente)
                if fase in ("CORRIDA", "PARADO_AUTORIZACAO", "SAIDA"):
                    if locacoes_candidatas:
                        loc_id = str(locacoes_candidatas[0])
                        if ocupantes_por_locacao.get(loc_id) in (None, trem_id):
                            ocupantes_por_locacao[loc_id] = trem_id
                            ocupantes.append(trem_id)
                        else:
                            bloqueados.append(trem_id)

                eventos = st["eventos"]
                # Semantica interna do despacho: `prog` = FRENTE; cauda e derivada.
                frente_atual = prog
                cauda_atual = (prog - tamanho_trem_t) if crescente else (prog + tamanho_trem_t)
                if eventos["t0"] is None and _cruzou_referencia(st["frente_anterior"], frente_atual, sinal_a_pos, crescente):
                    eventos["t0"] = tempo
                if eventos["t4"] is None and _cruzou_referencia(st["frente_anterior"], frente_atual, sinal_b_pos, crescente):
                    eventos["t4"] = tempo
                if eventos["t5"] is None and _cruzou_referencia(st["cauda_anterior"], cauda_atual, sinal_b_pos, crescente):
                    eventos["t5"] = tempo

                # Libera somente apos passagem da cauda (t5). Fallback: sem overlap em locacao.
                if fase == "SAIDA" and (eventos["t5"] is not None or not locacoes_candidatas):
                    if eventos["t5"] is None:
                        eventos["t5"] = tempo
                    st["fase"] = "LIBERADO"
                    st["liberado"] = True
                    status_operacional = "PARADO_LIBERADO"
                    vel = 0.0
                    acel = 0.0

                st["prog_atual"] = prog
                st["vel_atual"] = vel
                st["acel_atual"] = acel
                st["frente_anterior"] = frente_atual
                st["cauda_anterior"] = cauda_atual
                st["vel_anterior"] = vel

                trens_frame.append({
                    "id": trem_id,
                    "cor": cor_por_trem.get(trem_id, "#60a5fa"),
                    # Semantica de visualizacao: progressiva enviada para o renderer = FRENTE.
                    "progressiva_m": prog,
                    "velocidade_kmh": vel,
                    "aceleracao_mps2": acel,
                    "bloqueado": trem_id in bloqueados,
                    "status_operacional": status_operacional,
                    "eventos": dict(eventos),
                })

            ha_ocupacao = any(v is not None for v in ocupantes_por_locacao.values())
            ha_bloqueio = bool(bloqueados)
            if ha_bloqueio:
                estado_sinal_a = "VERMELHO"
                estado_sinal_b = "VERMELHO"
            elif ha_ocupacao:
                estado_sinal_a = "AMARELO"
                estado_sinal_b = "VERMELHO"
            else:
                estado_sinal_a = "AMARELO"
                estado_sinal_b = "AMARELO"

            frames.append({
                "tempo_s": tempo,
                "trens": trens_frame,
                "sinais": [
                    {"id": sinal_a_id, "estado": estado_sinal_a},
                    {"id": sinal_b_id, "estado": estado_sinal_b},
                ],
                "locacoes": [
                    {"id": loc_id, "ocupante_trem_id": trem_id}
                    for loc_id, trem_id in ocupantes_por_locacao.items()
                ],
                "conflito_ocupacao": False,
                "ocupantes": ocupantes,
                "bloqueados": bloqueados,
                "eventos_trens": {
                    tid: dict(estado_trens[tid]["eventos"]) for tid in ordem_trens
                },
            })

            if all(estado_trens[tid]["liberado"] for tid in ordem_trens):
                break

        return frames

    def selecionar_csv(self):
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.csv_fullpath = file_path
            try:
                if self.modo_livre:
                    grade.leGradeCsvLivre(file_path, self.check_var.get())
                else:
                    with open(file_path, mode='r', encoding='utf-8-sig', newline='') as file:
                        csv_reader = csv.reader(file)
                        first_line = next(csv_reader, None)
                        if len(first_line) != 3 or first_line[0] not in ['grade', 'grade_crescente'] or first_line[1] not in ['intervalo_grade'] or first_line[2] not in ['posicao']:
                            messagebox.showerror("Erro", "O arquivo selecionado não é um CSV de grade válido.")
                            return
            except Exception as exc:
                messagebox.showerror("Erro", f"CSV inválido: {exc}")
                return
            
            entrada_csv = os.path.basename(file_path)
            self.entry_csv.delete(0, tk.END)
            self.entry_csv.insert(0, entrada_csv)
            self._atualizar_progressiva_final_livre()
    
    def verifica_dados(self, params):
        if params['progressiva'] < 0:
            raise ValueError("A progressiva inicial não pode ser negativa.")
        if params['ponto_a_proteger'] < 0:
            raise ValueError("O ponto a proteger não pode ser negativo.")
        if params["tempo_parado_s"] < 0:
            raise ValueError("O tempo parado (T_parado) não pode ser negativo.")
        if params["quantidade_trens"] < 1:
            raise ValueError("A quantidade de trens deve ser pelo menos 1.")
        if params["step"] <= 0:
            raise ValueError("O step deve ser um número positivo.")
        if params["tamanho_trem"] <= 0:
            raise ValueError("O tamanho do trem deve ser um número positivo.")
        if params["tempo_freio_minimo_s"] < 0:
            raise ValueError("O tempo de freio mínimo não pode ser negativo.")
        if params["tempo_equalizacao_freio_s"] < 0:
            raise ValueError("O tempo de equalização do freio não pode ser negativo.")
        if params["velocidade_inicial_kmh"] < 0:
            raise ValueError("A velocidade inicial não pode ser negativa.")
        if params["vma_saida_kmh"] <= 0:
            raise ValueError("A VMA de saída deve ser um número positivo.")
        if params['taxa_frenagem'] >= 0:
            raise ValueError("A taxa de frenagem deve ser um número negativo (desaceleração).")
    
    def exportar(self):
        if not self.results:
            messagebox.showwarning("Exportar", "Nenhum resultado para exportar. Rode a simulação primeiro.")
            return

        output_path = filedialog.askdirectory(title="Selecione a pasta de destino para os arquivos exportados")
        
        if output_path == "":
            return

        # Exportar Aba Grade
        out_path = os.path.join(output_path, f"{self.locacao_nome}_grade_iteracoes_out.csv")
        with open(out_path, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.results['fieldnames'])
            writer.writeheader()
            writer.writerows(self.results['linhas'])
        
        # Exportar Aba Gráfico
        out_resumo = os.path.join(output_path, f"{self.locacao_nome}_grade_total_por_passo.csv")
        with open(out_resumo, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['iteracao', 'progressiva', 'grade_total'])
            writer.writeheader()
            writer.writerows(self.results['serie'])
        
        # Exporta os dados da corrida para CSV
        out_corrida = os.path.join(output_path, f"{self.locacao_nome}_aba_corrida_out.csv")
        with open(out_corrida, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['Tempo_s', 'Progressiva_m', 'Velocidade_kmh', 'Aceleracao_mps2', 'Variacao_Aceleracao_mps2', 'GradeTotal'],
            )
            writer.writeheader()
            writer.writerows(self.results["corrida"])
        
        messagebox.showinfo("Exportar", f"Arquivos da locação '{self.locacao_nome}' exportados com sucesso!")
    
    def preenche_tabela_corrida(self, corrida_linhas):
        self.tabela_corrida.delete(*self.tabela_corrida.get_children())
        for row in corrida_linhas:
            self.tabela_corrida.insert("", "end", values=(
                row.get("Tempo_s"),
                row.get("Velocidade_kmh"),
                row.get("Progressiva_m"),
                row.get("Aceleracao_mps2"),
                row.get("Variacao_Aceleracao_mps2"),
            ))
    
    def plota_corrida(self, corrida_linhas, crescente):
        self.ax_corrida.clear()
        self.ax_corrida_prog.clear()
        
        tempos = [row["Tempo_s"] for row in corrida_linhas]
        velocidades = [row["Velocidade_kmh"] for row in corrida_linhas]
        progressivas = [row["Progressiva_m"] for row in corrida_linhas]
                
        line1 = self.ax_corrida.plot(tempos, velocidades, "b-", linewidth=2, label="Velocidade (km/h)")
        line2 = self.ax_corrida_prog.plot(tempos, progressivas, "r-", linewidth=2, label="Progressiva (m)")
        
        self.ax_corrida.set_xlabel("Tempo (s)", fontsize=10)

        # Eixo esquerdo: velocidade
        self.ax_corrida.set_ylabel("Velocidade (km/h)", color="b", fontsize=10)
        self.ax_corrida.yaxis.set_label_position("left")
        self.ax_corrida.yaxis.tick_left()
        self.ax_corrida.tick_params(axis="y", left=True, labelleft=True, right=False, labelright=False, labelcolor="b")

        # Eixo direito: progressiva
        self.ax_corrida_prog.set_ylabel("Progressiva (m)", color="r", fontsize=10)
        self.ax_corrida_prog.yaxis.set_label_position("right")
        self.ax_corrida_prog.yaxis.tick_right()
        self.ax_corrida_prog.tick_params(axis="y", right=True, labelright=True, left=False, labelleft=False, labelcolor="r")
                
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        self.ax_corrida.legend(lines, labels, loc="upper left")
        
        self.ax_corrida.grid(True, alpha=0.3)
        self.fig_corrida.tight_layout()
        self.canvas_corrida.draw()
    
    def plota_grade(self, serie, crescente):
        self.ax_grade.clear()
        
        progressivas = [row["progressiva"] for row in serie]
        grades = [row["grade_total"] for row in serie]
        
        self.ax_grade.plot(progressivas, grades, "g-", linewidth=2)
        self.ax_grade.fill_between(progressivas, grades, alpha=0.3, color="green")
        
        self.ax_grade.set_xlabel("Progressiva (m)", fontsize=10)
        self.ax_grade.set_ylabel("Grade Total (%)", fontsize=10)
        self.ax_grade.grid(True, alpha=0.3)
        self.ax_grade.tick_params(axis="x", labelrotation=45)
        for label in self.ax_grade.get_xticklabels():
            label.set_ha("right")
        
        self.fig_grade.tight_layout()
        self.canvas_grade.draw()

    def plota_diagrama_espaco_tempo(self, frames, trens_cfg):
        self.ax_diagrama.clear()

        if not frames:
            self.ax_diagrama.set_title("Diagrama Espaço-Tempo")
            self.ax_diagrama.set_xlabel("Tempo (s)")
            self.ax_diagrama.set_ylabel("Progressiva (m)")
            self.ax_diagrama.grid(True, alpha=0.3)
            self.fig_diagrama.tight_layout()
            self.canvas_diagrama.draw()
            return

        cor_por_trem = {
            str(cfg.get("id")): cfg.get("cor", "#2563eb")
            for cfg in trens_cfg
            if str(cfg.get("id", ""))
        }

        series_por_trem = {}
        for frame in frames:
            tempo_s = float(frame.get("tempo_s", 0.0))
            for trem in frame.get("trens", []):
                trem_id = str(trem.get("id", ""))
                if not trem_id:
                    continue
                if trem_id not in series_por_trem:
                    series_por_trem[trem_id] = {"t": [], "p": []}
                series_por_trem[trem_id]["t"].append(tempo_s)
                series_por_trem[trem_id]["p"].append(float(trem.get("progressiva_m", 0.0)))

        for trem_id, serie in series_por_trem.items():
            self.ax_diagrama.plot(
                serie["t"],
                serie["p"],
                linewidth=2,
                color=cor_por_trem.get(trem_id, "#2563eb"),
                label=trem_id,
            )

        # Marca eventos operacionais t0..t5 no diagrama para facilitar leitura.
        eventos_finais = frames[-1].get("eventos_trens", {}) if frames else {}
        for trem_id, eventos in eventos_finais.items():
            if trem_id not in series_por_trem or not isinstance(eventos, dict):
                continue
            serie_t = series_por_trem[trem_id]["t"]
            serie_p = series_por_trem[trem_id]["p"]
            if not serie_t:
                continue

            for nome_evento in ("t0", "t1", "t2", "t3", "t4", "t5"):
                tempo_evt = eventos.get(nome_evento)
                if tempo_evt is None:
                    continue
                try:
                    tempo_evt = float(tempo_evt)
                except Exception:
                    continue
                idx = min(range(len(serie_t)), key=lambda i: abs(serie_t[i] - tempo_evt))
                self.ax_diagrama.scatter(
                    [serie_t[idx]],
                    [serie_p[idx]],
                    s=18,
                    color=cor_por_trem.get(trem_id, "#2563eb"),
                    zorder=3,
                )
                self.ax_diagrama.annotate(
                    nome_evento,
                    (serie_t[idx], serie_p[idx]),
                    textcoords="offset points",
                    xytext=(0, 5),
                    ha="center",
                    fontsize=8,
                )

        self.ax_diagrama.set_title("Diagrama Espaço-Tempo")
        self.ax_diagrama.set_xlabel("Tempo (s)")
        self.ax_diagrama.set_ylabel("Progressiva (m)")
        self.ax_diagrama.grid(True, alpha=0.3)
        self.ax_diagrama.legend(loc="best", fontsize=8)
        self.fig_diagrama.tight_layout()
        self.canvas_diagrama.draw()
    
    def atualiza_resumo(self, corrida_linhas):
        if not corrida_linhas:
            return
        
        # Extrair dados da última linha
        ultima_linha = corrida_linhas[-1]
        progressiva_parada = ultima_linha.get("Progressiva_m", "-")
        tempo_total = ultima_linha.get("Tempo_s", "-")
        distancia_percorrida = abs(float(ultima_linha.get("Progressiva_m", 0)) - float(self.entry_progressiva.get()))
        
        # Calcular métricas
        velocidades = [float(row.get("Velocidade_kmh", 0)) for row in corrida_linhas]
        vel_media_kmh = np.mean(velocidades) if velocidades else 0
        vel_media_ms = vel_media_kmh / 3.6
        
        # Headway operacional e capacidade
        tempo_total_s = float(tempo_total) if tempo_total != "-" else 0
        tempo_parado_cfg = 5.0
        if isinstance(self.last_params, dict):
            tempo_parado_cfg = float(self.last_params.get("tempo_parado_s", 5.0))

        tempo_saida_estimado_s = 0.0
        if isinstance(self.results, dict):
            tempo_saida_estimado_s = float(self.results.get("tempo_saida_estimado_s", 0.0) or 0.0)

        eventos_trens = {}
        if isinstance(self.results, dict):
            eventos_trens = self.results.get("eventos_trens", {}) or {}

        headway_por_trem = []
        headways_evento = []
        for trem_id, eventos in eventos_trens.items():
            if not isinstance(eventos, dict):
                continue
            t1 = eventos.get("t1")
            t2 = eventos.get("t2")
            t3 = eventos.get("t3")
            t4 = eventos.get("t4")
            t0 = eventos.get("t0")
            t5 = eventos.get("t5")

            t_percurso = None
            if t0 is not None and t1 is not None:
                t_percurso = float(t1) - float(t0)

            t_parado = None
            if t1 is not None and t3 is not None:
                t_parado = float(t3) - float(t1)
            elif t1 is not None:
                t_parado = tempo_parado_cfg

            t_saida = None
            if t3 is not None and t5 is not None:
                t_saida = float(t5) - float(t3)
            elif t5 is not None:
                t_saida = tempo_saida_estimado_s

            hw = None
            if t0 is not None and t5 is not None:
                hw = float(t5) - float(t0)
                if hw >= 0:
                    headways_evento.append(hw)

            headway_por_trem.append({
                "trem_id": str(trem_id),
                "t0": t0,
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "t4": t4,
                "t5": t5,
                "t_percurso": t_percurso,
                "t_parado": t_parado,
                "t_saida": t_saida,
                "headway": hw,
            })

        # Consolidado operacional: maior headway observado (critico do trecho).
        headway = max(headways_evento) if headways_evento else 0.0

        # Fallback durante transicao: quando t0/t5 ainda nao estiverem disponiveis.
        if headway <= 0 and tempo_total_s > 0:
            headway = tempo_total_s + tempo_parado_cfg + tempo_saida_estimado_s

        cap_teorica = (3600 / headway) if headway > 0 else 0
        cap_pratica = cap_teorica * 0.85
        
        # Distância de proteção
        distancia_protecao = abs(float(self.entry_ponto_a_proteger.get()) - float(ultima_linha.get("Progressiva_m", 0)))
        
        # Distância entre sinais
        distancia_sinais = abs(float(self.entry_ponto_a_proteger.get()) - float(self.entry_progressiva.get()))
        
        # Tempo de ocupacao: frenagem + parado + saida.
        tempo_ocupacao = tempo_total_s + tempo_parado_cfg + tempo_saida_estimado_s
        
        self.var_prog_parada.set(f"{progressiva_parada:.2f}")
        self.var_tempo_total.set(f"{tempo_ocupacao:.2f}")
        self.var_dist_perc.set(f"{distancia_percorrida:.2f}")
        self.var_dist_protecao.set(f"{distancia_protecao:.2f}")
        self.var_dist_sinais.set(f"{distancia_sinais:.2f}")
        self.var_vel_med.set(f"{vel_media_ms:.2f}")
        self.var_headway.set(f"{headway:.2f}")
        self.var_cap_teor.set(f"{cap_teorica:.2f}")
        self.var_cap_prat.set(f"{cap_pratica:.2f}")
        
        self.resumo = {
            "progressiva_parada": progressiva_parada,
            "tempo_total": tempo_total,
            "distancia_percorrida": distancia_percorrida,
            "distancia_protecao": distancia_protecao,
            "distancia_sinais": distancia_sinais,
            "velocidade_media_ms": vel_media_ms,
            "tempo_ocupacao": tempo_ocupacao,
            "tempo_parado_cfg_s": tempo_parado_cfg,
            "tempo_saida_estimado_s": tempo_saida_estimado_s,
            "headway": headway,
            "headways_evento": headways_evento,
            "headway_por_trem": headway_por_trem,
            "capacidade_teorica": cap_teorica,
            "capacidade_pratica": cap_pratica,
        }


class RelatorioPrincipal:
    """Tela de relatório consolidado"""
    EVENTO_LABELS = {
        "t0": "Entrada A",
        "t1": "Parada B",
        "t2": "Autorização",
        "t3": "Retomada",
        "t4": "Frente B",
        "t5": "Cauda B",
    }

    def __init__(self, parent_notebook, main_app=None):
        self.main_app = main_app
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text="Relatório")
        
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=0)
        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)
        
        # Título
        titulo = ttk.Label(self.frame, text="Relatório Consolidado de Locações", font=("Arial", 16, "bold"))
        titulo.grid(row=0, column=0, sticky="ew", padx=10, pady=10)


        # Tabela de resumo
        self.tabela_resumo = ttk.Treeview(
            self.frame,
            columns=("Locacao", "Progressiva Parada", "Tempo Ocupacao", "Distancia Percorrida", "Capacidade Teórica", "Capacidade Prática", "Headway"),
            show="headings",
        )
        self.tabela_resumo.heading("Locacao", text="Locação")
        self.tabela_resumo.heading("Progressiva Parada", text="Progressiva Parada (m)")
        self.tabela_resumo.heading("Tempo Ocupacao", text="Tempo Ocupação (s)")
        self.tabela_resumo.heading("Distancia Percorrida", text="Distância Percorrida (m)")
        self.tabela_resumo.heading("Capacidade Teórica", text="Capacidade Teórica (trens/h)")
        self.tabela_resumo.heading("Capacidade Prática", text="Capacidade Prática (trens/h)")
        self.tabela_resumo.heading("Headway", text="Headway Crítico (s)")
        
        self.tabela_resumo.column("Locacao", width=100, anchor="center")
        self.tabela_resumo.column("Progressiva Parada", width=150, anchor="center")
        self.tabela_resumo.column("Tempo Ocupacao", width=120, anchor="center")
        self.tabela_resumo.column("Distancia Percorrida", width=150, anchor="center")
        self.tabela_resumo.column("Capacidade Teórica", width=150, anchor="center")
        self.tabela_resumo.column("Capacidade Prática", width=150, anchor="center")
        self.tabela_resumo.column("Headway", width=120, anchor="center")

        self.tabela_resumo.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        scroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.tabela_resumo.yview)
        self.tabela_resumo.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=10)

        self.frame_detalhe_headway = ttk.LabelFrame(self.frame, text="Detalhes de Headway por Trem")
        self.frame_detalhe_headway.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.frame_detalhe_headway.columnconfigure(0, weight=1)
        self.frame_detalhe_headway.rowconfigure(0, weight=1)

        self.tabela_headway_trem = ttk.Treeview(
            self.frame_detalhe_headway,
            columns=(
                "Locacao",
                "Trem",
                "t0",
                "t1",
                "t2",
                "t3",
                "t4",
                "t5",
                "T_percurso",
                "T_parado",
                "T_saida",
                "Headway",
            ),
            show="headings",
            height=8,
        )
        self.tabela_headway_trem.heading("Locacao", text="Locação")
        self.tabela_headway_trem.heading("Trem", text="Trem")
        self.tabela_headway_trem.heading("t0", text=f"{self.EVENTO_LABELS['t0']} (s)")
        self.tabela_headway_trem.heading("t1", text=f"{self.EVENTO_LABELS['t1']} (s)")
        self.tabela_headway_trem.heading("t2", text=f"{self.EVENTO_LABELS['t2']} (s)")
        self.tabela_headway_trem.heading("t3", text=f"{self.EVENTO_LABELS['t3']} (s)")
        self.tabela_headway_trem.heading("t4", text=f"{self.EVENTO_LABELS['t4']} (s)")
        self.tabela_headway_trem.heading("t5", text=f"{self.EVENTO_LABELS['t5']} (s)")
        self.tabela_headway_trem.heading("T_percurso", text="Tempo Percurso (s)")
        self.tabela_headway_trem.heading("T_parado", text="Tempo Parado (s)")
        self.tabela_headway_trem.heading("T_saida", text="Tempo Saída (s)")
        self.tabela_headway_trem.heading("Headway", text="Headway (s)")

        self.tabela_headway_trem.column("Locacao", width=100, anchor="center")
        self.tabela_headway_trem.column("Trem", width=80, anchor="center")
        for col in ("t0", "t1", "t2", "t3", "t4", "t5", "T_percurso", "T_parado", "T_saida", "Headway"):
            self.tabela_headway_trem.column(col, width=100, anchor="center")

        self.tabela_headway_trem.grid(row=0, column=0, sticky="nsew")

        self.scroll_headway_trem = ttk.Scrollbar(self.frame_detalhe_headway, orient=tk.VERTICAL, command=self.tabela_headway_trem.yview)
        self.tabela_headway_trem.configure(yscrollcommand=self.scroll_headway_trem.set)
        self.scroll_headway_trem.grid(row=0, column=1, sticky="ns")

        self.atualizar_relatorio()
    
    def atualizar_relatorio(self):
        self.tabela_resumo.delete(*self.tabela_resumo.get_children())
        self.tabela_headway_trem.delete(*self.tabela_headway_trem.get_children())
        
        if not self.main_app or not self.main_app.locacoes:
            return
        
        for locacao_id, locacao_ui in self.main_app.locacoes.items():
            if locacao_ui.resumo:
                resumo = locacao_ui.resumo
                self.tabela_resumo.insert("", "end", values=(
                    locacao_ui.locacao_nome,
                    f"{resumo.get('progressiva_parada', '-')}",
                    f"{resumo.get('tempo_ocupacao', 0.0):.2f}",
                    f"{resumo.get('distancia_percorrida', '-'):.2f}",
                    f"{resumo.get('capacidade_teorica', '-'):.2f}",
                    f"{resumo.get('capacidade_pratica', '-'):.2f}",
                    f"{resumo.get('headway', '-'):.2f}",
                ))

                for item in resumo.get("headway_por_trem", []):
                    def _fmt(v):
                        if v is None:
                            return "-"
                        try:
                            return f"{float(v):.2f}"
                        except Exception:
                            return str(v)

                    self.tabela_headway_trem.insert("", "end", values=(
                        locacao_ui.locacao_nome,
                        item.get("trem_id", "-"),
                        _fmt(item.get("t0")),
                        _fmt(item.get("t1")),
                        _fmt(item.get("t2")),
                        _fmt(item.get("t3")),
                        _fmt(item.get("t4")),
                        _fmt(item.get("t5")),
                        _fmt(item.get("t_percurso")),
                        _fmt(item.get("t_parado")),
                        _fmt(item.get("t_saida")),
                        _fmt(item.get("headway")),
                    ))


class GUIApp:
    """Aplicação principal com gerenciamento de locações"""
    def __init__(self, master):
        self.master = master
        self.master.title("Simulação - Curvas de Frenagem (Multi-Locação)")
        self.master.geometry("1450x850")
        self.master.resizable(True, True)
        
        self.locacoes = {}  # {id: LocalizacaoUI}
        self.contador_locacoes = 0
        self.relatorio_ui = None
        
        # --- MENU ---
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        menu_locacoes = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Locações", menu=menu_locacoes)
        menu_locacoes.add_command(label="Adicionar Locação", command=self.adicionar_locacao)
        menu_locacoes.add_command(label="Adicionar Locação Livre", command=lambda: self.adicionar_locacao(modo_livre=True))
        menu_locacoes.add_command(label="Renomear Locação", command=self.renomear_locacao)
        menu_locacoes.add_command(label="Remover Locação", command=self.remover_locacao)
        menu_locacoes.add_separator()
        menu_locacoes.add_command(label="Exportar Todas as Locações", command=self.exportar_todas)
        
        # --- NOTEBOOK PRINCIPAL ---
        self.notebook_principal = ttk.Notebook(self.master)
        self.notebook_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Adicionar primeira locação padrão
        self.adicionar_locacao("Locação 1")
        
        # Adicionar aba de relatório
        self.relatorio_ui = RelatorioPrincipal(self.notebook_principal, main_app=self)
    
    def adicionar_locacao(self, nome=None, modo_livre=False):
        proximo_id = self._proximo_id_locacao()
        
        if nome is None:
            # Pedir nome ao usuário
            if modo_livre:
                nome = simpledialog.askstring(
                "Nova Locação Livre",
                f"Digite o nome da locação:",
                initialvalue=f"Locação Livre {proximo_id}"
            )
            else:
                nome = simpledialog.askstring(
                    "Nova Locação",
                    f"Digite o nome da locação:",
                    initialvalue=f"Locação {proximo_id}"
                )
            if not nome:
                return
        
        locacao_id = proximo_id
        self.contador_locacoes = max(self.contador_locacoes, locacao_id)
        locacao_ui = LocalizacaoUI(
            self.notebook_principal,
            locacao_id,
            locacao_nome=nome,
            main_app=self
        )
        if modo_livre:
            locacao_ui.ativar_modo_livre()
        self.locacoes[locacao_id] = locacao_ui
        
        # Mantem o relatorio sempre como ultima aba (quando ele ja existe)
        if self.relatorio_ui is not None:
            self.notebook_principal.insert("end", self.relatorio_ui.frame)
        
        tipo_locacao = "Locação Livre" if modo_livre else "Locação"
        messagebox.showinfo("Sucesso", f"{tipo_locacao} '{nome}' adicionada com sucesso!")

    def _proximo_id_locacao(self, modo_livre=False):
        usados = set(self.locacoes.keys())
        candidato = 1

        while candidato in usados:
            candidato += 1
            
        return candidato

    def renomear_locacao(self):
        """Permite ao usuário renomear uma locação existente"""
        if not self.locacoes:
            messagebox.showwarning("Renomear", "Nenhuma locação para renomear!")
            return
        
        # Criar diálogo para selecionar qual locação renomear
        opcoes = [f"{self.locacoes[lid].locacao_nome} (ID: {lid})" for lid in sorted(self.locacoes.keys())]
        
        top = tk.Toplevel(self.master)
        top.title("Renomear Locação")
        top.geometry("350x220")
        
        ttk.Label(top, text="Selecione a locação:", font=("Arial", 10)).pack(padx=10, pady=10)
        
        var_opcao = tk.StringVar()
        combo = ttk.Combobox(top, textvariable=var_opcao, values=opcoes, state="readonly", width=35)
        combo.pack(padx=10, pady=5)
        combo.current(0)
        
        ttk.Label(top, text="Novo nome:", font=("Arial", 10)).pack(padx=10, pady=(10, 0))
        entry_novo_nome = ttk.Entry(top, width=35)
        entry_novo_nome.pack(padx=10, pady=5)
        
        # Preencher o entry com o nome atual selecionado
        def _atualizar_entry(*args):
            idx = combo.current()
            if idx >= 0:
                locacao_id = sorted(self.locacoes.keys())[idx]
                nome_atual = self.locacoes[locacao_id].locacao_nome
                entry_novo_nome.delete(0, tk.END)
                entry_novo_nome.insert(0, nome_atual)
        
        combo.bind("<<ComboboxSelected>>", _atualizar_entry)
        _atualizar_entry()
        
        def confirmar_renomeacao():
            idx = combo.current()
            if idx < 0:
                messagebox.showwarning("Erro", "Selecione uma locação!")
                return
            
            novo_nome = entry_novo_nome.get().strip()
            if not novo_nome:
                messagebox.showwarning("Erro", "O nome não pode estar vazio!")
                return
            
            locacao_id = sorted(self.locacoes.keys())[idx]
            locacao_ui = self.locacoes[locacao_id]
            nome_anterior = locacao_ui.locacao_nome
            
            # Atualizar nome na LocalizacaoUI
            locacao_ui.locacao_nome = novo_nome
            
            # Atualizar o label do frame_inputs
            locacao_ui.frame_inputs.configure(text=f"Parâmetros - {novo_nome}")
            
            # Atualizar o label da aba de resultados (tab do notebook de resultados)
            locacao_ui.label.configure(text=f"Simulação - {novo_nome}")
            
            # Atualizar o label da aba no notebook principal
            tab_index = self.notebook_principal.index(locacao_ui.frame)
            self.notebook_principal.tab(tab_index, text=novo_nome)
            
            # Atualizar relatório
            self.atualiza_dados_relatorio()
            
            top.destroy()
            messagebox.showinfo("Sucesso", f"Locação '{nome_anterior}' renomeada para '{novo_nome}'!")
        
        btn_confirmar = ttk.Button(top, text="Renomear", command=confirmar_renomeacao)
        btn_confirmar.pack(padx=10, pady=10)
    
    def remover_locacao(self):
        if not self.locacoes:
            messagebox.showwarning("Remover", "Nenhuma locação para remover!")
            return
        
        # Criar diálogo para selecionar qual locação remover
        opcoes = [f"{self.locacoes[lid].locacao_nome} (ID: {lid})" for lid in sorted(self.locacoes.keys())]
        
        top = tk.Toplevel(self.master)
        top.title("Remover Locação")
        top.geometry("300x200")
        
        ttk.Label(top, text="Selecione a locação para remover:", font=("Arial", 10)).pack(padx=10, pady=10)
        
        var_opcao = tk.StringVar()
        combo = ttk.Combobox(top, textvariable=var_opcao, values=opcoes, state="readonly", width=30)
        combo.pack(padx=10, pady=5)
        
        def confirmar_remocao():
            idx = combo.current()
            if idx < 0:
                messagebox.showwarning("Erro", "Selecione uma locação!")
                return
            
            locacao_id = sorted(self.locacoes.keys())[idx]
            locacao_ui = self.locacoes[locacao_id]
            
            confirm = messagebox.askyesno(
                "Confirmar",
                f"Remover locação '{locacao_ui.locacao_nome}'?\nEsta ação não pode ser desfeita."
            )
            
            if confirm:
                self.notebook_principal.forget(locacao_ui.frame)
                del self.locacoes[locacao_id]
                self.atualiza_dados_relatorio()
                top.destroy()
                messagebox.showinfo("Sucesso", f"Locação removida com sucesso!")
        
        btn_confirmar = ttk.Button(top, text="Remover", command=confirmar_remocao)
        btn_confirmar.pack(padx=10, pady=10)
    
    def atualiza_dados_relatorio(self):
        """Atualiza a aba de relatório com dados das locações"""
        if self.relatorio_ui:
            self.relatorio_ui.atualizar_relatorio()
    
    def exportar_todas(self):
        if not self.locacoes:
            messagebox.showwarning("Exportar", "Nenhuma locação para exportar!")
            return
        
        output_path = filedialog.askdirectory(title="Selecione a pasta de destino")
        if not output_path:
            return
        
        locacoes_exportadas = 0
        for locacao_id, locacao_ui in self.locacoes.items():
            if locacao_ui.results:
                try:
                    # Exportar Aba Grade
                    out_path = os.path.join(output_path, f"{locacao_ui.locacao_nome}_grade_iteracoes_out.csv")
                    with open(out_path, mode='w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=locacao_ui.results['fieldnames'])
                        writer.writeheader()
                        writer.writerows(locacao_ui.results['linhas'])
                    
                    # Exportar Aba Gráfico
                    out_resumo = os.path.join(output_path, f"{locacao_ui.locacao_nome}_grade_total_por_passo.csv")
                    with open(out_resumo, mode='w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['iteracao', 'progressiva', 'grade_total'])
                        writer.writeheader()
                        writer.writerows(locacao_ui.results['serie'])
                    
                    # Exportar dados da corrida
                    out_corrida = os.path.join(output_path, f"{locacao_ui.locacao_nome}_aba_corrida_out.csv")
                    with open(out_corrida, mode='w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(
                            f,
                            fieldnames=['Tempo_s', 'Progressiva_m', 'Velocidade_kmh', 'Aceleracao_mps2', 'Variacao_Aceleracao_mps2', 'GradeTotal'],
                        )
                        writer.writeheader()
                        writer.writerows(locacao_ui.results["corrida"])
                    
                    locacoes_exportadas += 1
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao exportar '{locacao_ui.locacao_nome}': {str(e)}")
        
        messagebox.showinfo("Exportar", f"{locacoes_exportadas} locação(ões) exportada(s) com sucesso!")

def main():
    root = tk.Tk()
    app = GUIApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
