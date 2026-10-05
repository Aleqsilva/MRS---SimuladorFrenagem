# Simulador de Frenagem Ferroviária (Braking Distance Simulator)

> Aplicação desktop para cálculo físico, simulação de dinâmica de frenagem e animação visual de composições ferroviárias baseada em rampas (grades) e parâmetros de trem.

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-Tkinter%20Pure-blue?style=for-the-badge)](https://docs.python.org/3/library/tkinter.html)
[![Physics](https://img.shields.io/badge/Model-Applied%20Physics-orange?style=for-the-badge)](#)

---

## Sobre o Projeto

O **Simulador de Frenagem** foi desenvolvido para analisar e visualizar a distância de parada de trens sob diferentes condições operacionais e de via. 

A frenagem de uma composição ferroviária é um processo complexo que depende do comprimento total do trem, distribuição de massa, velocidade inicial e, principalmente, do perfil altimétrico da via (grade/rampa). O software executa o cálculo físico da desaceleração até o repouso absoluto ($v = 0$), determinando se o trem é capaz de parar com segurança antes de um determinado marco de sinalização ou ponto de controle.

---

## Arquitetura e Estrutura Modular

O projeto foi construído seguindo uma arquitetura modular limpa e desacoplada em 5 arquivos principais, dividindo claramente a física, o processamento de dados e a camada visual:

```text
Simulador-Frenagem/
├── main.py           # Ponto de entrada da aplicação e inicialização
├── gui.py            # Interface gráfica do usuário (Tkinter Pure)
├── corrida.py        # Motor de cálculo físico e equações de desaceleração
├── pipeline.py       # Extração, tratamento e estruturação dos dados de entrada
└── simulacao.py      # Renderizador gráfico e animação da composição na via
