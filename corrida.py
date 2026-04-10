import numpy as np


def _normaliza_vmas(vmas):
    resultado = []
    for item in vmas or []:
        inicio = float(item.get("inicio"))
        fim = float(item.get("fim"))
        vma = float(item.get("vma_kmh"))
        if vma <= 0:
            continue
        a = min(inicio, fim)
        b = max(inicio, fim)
        resultado.append({"inicio": a, "fim": b, "vma_kmh": vma})
    resultado.sort(key=lambda x: (x["inicio"], x["fim"]))
    return resultado


def _normaliza_pausas(pausas):
    resultado = []
    for item in pausas or []:
        p = float(item.get("progressiva"))
        d = float(item.get("duracao_s"))
        if d <= 0:
            continue
        resultado.append({"progressiva": p, "duracao_s": d, "executada": False})
    return resultado


def _vma_na_progressiva(progressiva, vmas):
    vma_aplicada = None
    for faixa in vmas:
        if faixa["inicio"] <= float(progressiva) <= faixa["fim"]:
            if vma_aplicada is None:
                vma_aplicada = float(faixa["vma_kmh"])
            else:
                vma_aplicada = min(vma_aplicada, float(faixa["vma_kmh"]))
    return vma_aplicada


def _cruzou_progressiva(anterior, atual, alvo, crescente):
    alvo = float(alvo)
    a = float(anterior)
    b = float(atual)
    if crescente:
        return (a < alvo <= b) or abs(b - alvo) <= 1e-9
    return (a > alvo >= b) or abs(b - alvo) <= 1e-9

def lookup_floor(x_query, x_ref, y_ref, *, default=np.nan):
    """Lookup tipo PROCV aproximado (arredonda para baixo).

    Retorna y_ref[i] onde x_ref[i] é o maior valor <= x_query.
    Assume x_ref ordenado crescente (se não estiver, ordena internamente).
    """
    x_ref = np.asarray(x_ref, dtype=float)
    y_ref = np.asarray(y_ref, dtype=float)
    if x_ref.size == 0:
        return default

    order = np.argsort(x_ref)
    x_ref = x_ref[order]
    y_ref = y_ref[order]

    idx = np.searchsorted(x_ref, x_query, side='right') - 1
    if idx < 0 or idx >= x_ref.size:
        return default
    return float(y_ref[idx])


def calculaAceleracaoCorrida(
    tempo_atual,
    tempo_freio_minimo,
    tempo_equalizacao_freio,
    taxa_frenagem,
    variacao_aceleracao,
    grade_total,
    crescente
):
    """Aceleração total (m/s²), compondo freio + influência de grade.

    Interpretação usada:
    - termo de grade = -grade_total/10
      (subida => grade_total positivo => aceleração negativa)
    - antes do freio: só grade
    - durante equalização: variacao_aceleracao + grade
    - após equalização: variacao_aceleracao + grade
    """


    termo_grade = (-float(grade_total) / 10.0)

    if tempo_atual < tempo_freio_minimo:
        return termo_grade
    elif tempo_atual > tempo_equalizacao_freio:
        return taxa_frenagem + termo_grade
    else:
        return float(variacao_aceleracao) + termo_grade


def simulaAbaCorrida(
    serie_progressiva,
    serie_grade_total,
    progressiva_inicial,
    velocidade_inicial_kmh,
    crescente,
    passo_de_tempo_s=0.5,
    tempo_freio_minimo_s=10.0,
    tempo_equalizacao_freio_s=39.9,
    taxa_frenagem=-0.155,
    lookahead_m=5.0,
    tempo_max_s=600.0,
    regras_operacionais=None,
):
    """Gera as linhas da Aba Corrida.

    Para cada passo de tempo:
    - Atualiza progressiva usando a física (velocidade anterior e aceleração anterior)
    - Faz lookup do grade_total na progressiva (com lookahead) usando PROCV aproximado
    - Calcula aceleração e velocidade
    - Atualiza variacao_aceleracao
    Para quando a velocidade chega a 0 ou quando sai do domínio do lookup.
    """
    if passo_de_tempo_s <= 0:
        raise ValueError("passo_de_tempo_s deve ser > 0")

    dx_lookahead = float(lookahead_m) if crescente else -float(lookahead_m) 

    linhas = []
    tempo = 0.0
    progressiva = float(progressiva_inicial)
    velocidade = float(velocidade_inicial_kmh)
    variacao_aceleracao = 0.0
    regras_operacionais = regras_operacionais or {}
    vmas = _normaliza_vmas(regras_operacionais.get("vmas", []))
    pausas = _normaliza_pausas(regras_operacionais.get("pausas", []))
    pausa_ativa_ate = None

    # aceleração inicial calculada (consistente com a regra da planilha)
    grade0 = lookup_floor(progressiva + dx_lookahead, serie_progressiva, serie_grade_total, default=np.nan)
    if np.isnan(grade0):
        raise ValueError("Lookup de grade_total falhou na progressiva inicial (fora do domínio da série).")
    
    aceleracao = calculaAceleracaoCorrida(
        tempo,
        tempo_freio_minimo_s,
        tempo_equalizacao_freio_s,
        taxa_frenagem,
        variacao_aceleracao,
        grade0,
        crescente
    )

    vma0 = _vma_na_progressiva(progressiva, vmas)
    if vma0 is not None:
        velocidade = min(float(velocidade), float(vma0))

    linhas.append({
        'Velocidade_kmh': velocidade,
        'Progressiva_m': progressiva,
        'Tempo_s': tempo,
        'Aceleracao_mps2': aceleracao,
        'Variacao_Aceleracao_mps2': variacao_aceleracao,
        'GradeTotal': grade0,
        'VMA_Aplicada_kmh': vma0,
        'Pausa_Ativa': False,
    })

    while tempo < tempo_max_s:
        tempo_anterior = tempo
        progressiva_anterior = progressiva
        velocidade_anterior = velocidade
        aceleracao_anterior = aceleracao
        variacao_anterior = variacao_aceleracao

        # tempo
        tempo = tempo_anterior + float(passo_de_tempo_s)

        if pausa_ativa_ate is not None and tempo <= pausa_ativa_ate + 1e-9:
            progressiva = progressiva_anterior
            grade_total = lookup_floor(progressiva + dx_lookahead, serie_progressiva, serie_grade_total, default=np.nan)
            if np.isnan(grade_total):
                break
            variacao_aceleracao = 0.0
            aceleracao = 0.0
            velocidade = 0.0

            linhas.append({
                'Tempo_s': tempo,
                'Progressiva_m': progressiva,
                'Velocidade_kmh': velocidade,
                'Aceleracao_mps2': aceleracao,
                'Variacao_Aceleracao_mps2': variacao_aceleracao,
                'GradeTotal': grade_total,
                'VMA_Aplicada_kmh': _vma_na_progressiva(progressiva, vmas),
                'Pausa_Ativa': True,
            })

            if tempo >= pausa_ativa_ate - 1e-9:
                pausa_ativa_ate = None
            continue

        # progressiva
        progressiva = calculaProgressiva(
            velocidade_anterior,
            progressiva_anterior,
            crescente,
            float(passo_de_tempo_s),
            aceleracao_anterior,
        )

        pausa_disparada = None
        for pausa in pausas:
            if pausa["executada"]:
                continue
            if _cruzou_progressiva(progressiva_anterior, progressiva, pausa["progressiva"], crescente):
                pausa_disparada = pausa
                break

        if pausa_disparada is not None:
            pausa_disparada["executada"] = True
            progressiva = float(pausa_disparada["progressiva"])
            pausa_ativa_ate = tempo + float(pausa_disparada["duracao_s"])

            grade_total = lookup_floor(progressiva + dx_lookahead, serie_progressiva, serie_grade_total, default=np.nan)
            if np.isnan(grade_total):
                break

            variacao_aceleracao = 0.0
            aceleracao = 0.0
            velocidade = 0.0
            linhas.append({
                'Tempo_s': tempo,
                'Progressiva_m': progressiva,
                'Velocidade_kmh': velocidade,
                'Aceleracao_mps2': aceleracao,
                'Variacao_Aceleracao_mps2': variacao_aceleracao,
                'GradeTotal': grade_total,
                'VMA_Aplicada_kmh': _vma_na_progressiva(progressiva, vmas),
                'Pausa_Ativa': True,
            })
            continue

        # grade_total com lookahead
        grade_total = lookup_floor(progressiva + dx_lookahead, serie_progressiva, serie_grade_total, default=np.nan)
        if np.isnan(grade_total):
            break


        # variação de aceleração (para ser usada na próxima linha)
        variacao_aceleracao = variacaoAceleracao(
            tempo,
            tempo_freio_minimo_s,
            variacao_aceleracao,
            variacao_anterior,
            taxa_frenagem,
            tempo_equalizacao_freio_s,
        )

        # aceleração (usa variacao_aceleracao atual)
        aceleracao = calculaAceleracaoCorrida(
            tempo,
            tempo_freio_minimo_s,
            tempo_equalizacao_freio_s,
            taxa_frenagem,
            variacao_aceleracao,
            grade_total,
            crescente
        )

        # velocidade
        velocidade = calculaVelocidade(velocidade_anterior, float(passo_de_tempo_s), aceleracao)
        if velocidade is None:
            break

        vma_local = _vma_na_progressiva(progressiva, vmas)
        if vma_local is not None:
            velocidade = min(float(velocidade), float(vma_local))
        
        linhas.append({
            'Tempo_s': tempo,
            'Progressiva_m': progressiva,
            'Velocidade_kmh': velocidade,
            'Aceleracao_mps2': aceleracao,
            'Variacao_Aceleracao_mps2': variacao_aceleracao,
            'GradeTotal': grade_total,
            'VMA_Aplicada_kmh': vma_local,
            'Pausa_Ativa': False,
        })

        if velocidade <= 0.0:
            break

    return linhas

def calculaVelocidade(velocidade_inicial, passo_de_tempo, aceleracao_inicial):
    if velocidade_inicial < 0:
        print("Erro: A velocidade inicial não pode ser negativa.")
        return None
    
    if passo_de_tempo < 0:
        print("Erro: O passo de tempo não pode ser negativo.")
        return None
    
    velocidade_mps = velocidade_inicial/3.6
    velocidade_atual = 0 if (velocidade_mps + (aceleracao_inicial * passo_de_tempo))*3.6 < 0 else (velocidade_mps + (aceleracao_inicial * passo_de_tempo))*3.6
    return velocidade_atual

def calculaProgressiva(velocidade_anterior, progressiva_anterior, crescente, passo_de_tempo, aceleracao_anterior):
    if velocidade_anterior == 0:
        Progressiva = progressiva_anterior
    elif crescente:
        Progressiva = progressiva_anterior + (velocidade_anterior/3.6)*(passo_de_tempo) + aceleracao_anterior * ((passo_de_tempo)**2)/2
    else:
        Progressiva = progressiva_anterior - (velocidade_anterior/3.6)*(passo_de_tempo) + aceleracao_anterior * ((passo_de_tempo)**2)/2
            
    return Progressiva

def variacaoAceleracao(tempo_atual, tempo_freio_minimo, variacao_aceleracao, variacao_anterior, taxa_frenagem, tempo_equalizacao_freio):
    if tempo_atual < tempo_freio_minimo:
        variacao_aceleracao = 0
    elif tempo_atual > tempo_equalizacao_freio:
        variacao_aceleracao = 0
    else:
        variacao_aceleracao = variacao_anterior + taxa_frenagem / (2*(tempo_equalizacao_freio - tempo_freio_minimo))
 
    return variacao_aceleracao